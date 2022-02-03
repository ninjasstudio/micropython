# https://github.com/m-lundberg/simple-pid.git
# http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-introduction/
# https://github.com/br3ttb/Arduino-PID-Library


@micropython.native
def _clamp(value, limits):
    if value is None:
        return None
    lower, upper = limits
    if (upper is not None) and (value > upper):
        return upper
    if (lower is not None) and (value < lower):
        return lower
    return value


@micropython.native
def _clamp_pad(value, limits):
    if value is None:
        return None
    lower, upper = limits
    if (upper is not None) and (value >= 0) and (value <= upper):
        return upper
    if (lower is not None) and (value <= 0) and (value >= lower):
        return lower
    return value


@micropython.native
def _cutoffs(value, cutoffs):
    if value is None:
        return None
    lower, upper = cutoffs
    if (upper is not None) and (value >= 0) and (value <= upper):
        return 0
    if (lower is not None) and (value <= 0) and (value >= lower):
        return 0
    return value


class PID(object):
    """A simple PID controller."""

    # yapf: disable
    def __init__(
        self,
        Kp=1,
        Ki=0,
        Kd=0,
        setpoint=0,
        sample_time=None,
        output_limits=(None, None),
        output_pads=(None, None),
        output_cutoffs=(None, None),
        auto_mode=True,
        proportional_on_measurement=False,
        error_map=None
    ):
        # yapf: enable
        """
        Initialize a new PID controller.

        :param Kp: The value for the proportional gain Kp
        :param Ki: The value for the integral gain Ki
        :param Kd: The value for the derivative gain Kd
        :param setpoint: The initial setpoint that the PID will try to achieve
        :param sample_time: The time in seconds which the controller should wait before generating
            a new output value. The PID works best when it is constantly called (eg. during a
            loop), but with a sample time set so that the time difference between each update is
            (close to) constant. If set to None, the PID will compute a new output value every time
            it is called.
        :param output_limits: The initial output limits to use, given as an iterable with 2
            elements, for example: (lower, upper). The output will never go below the lower limit
            or above the upper limit. Either of the limits can also be set to None to have no limit
            in that direction. Setting output limits also avoids integral windup, since the
            integral term will never be allowed to grow outside of the limits.
        :param auto_mode: Whether the controller should be enabled (auto mode) or not (manual mode)
        :param proportional_on_measurement: Whether the proportional term should be calculated on
            the input directly rather than on the error (which is the traditional way). Using
            proportional-on-measurement avoids overshoot for some types of systems.
        :param error_map: Function to transform the error value in another constrained value.
        """
        """
        Инициализировать новый ПИД-регулятор.

        :param Kp: Значение пропорционального усиления Kp
        :param Ki: значение интегрального усиления Ki
        :param Kd: Значение производной усиления Kd
        :param setpoint: Начальная уставка, которую ПИД будет пытаться достичь.
        :param sample_time: Время в секундах, в течение которого контроллер должен ждать перед
            генерацией нового выходного значения. PID работает лучше всего, когда он вызывается постоянно
            (например, во время цикла), но с установленным временем выборки так, чтобы разница во времени
            между каждым обновлением была (близка к) постоянной. Если установлено значение None, PID будет
            вычислять новое выходное значение каждый раз при его вызове.
        :param output_limits: Начальные пределы вывода для использования, заданные как итерация с двумя элементами,
            например: (нижний, верхний). Выходной сигнал никогда не будет ниже нижнего или выше верхнего предела.
            Для любого из ограничений также можно установить значение «Нет», чтобы не было ограничений в этом направлении.
            Установка пределов вывода также позволяет избежать интегрального нарастания,
            так как интегральный член никогда не сможет вырасти за пределы.
        :param auto_mode: Должен ли контроллер быть включен (автоматический режим) или нет (ручной режим)
        :param ratio_on_measurement: Должен ли пропорциональный член вычисляться непосредственно на входе,
            а не на ошибке (что является традиционным способом). Использование пропорционального измерения
            позволяет избежать перерегулирования для некоторых типов систем.
        """
        self.direction = 1
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.setpoint = setpoint
        self.sample_time = sample_time

        self._min_output, self._max_output = None, None
        self._auto_mode = auto_mode
        self.proportional_on_measurement = proportional_on_measurement
        self.error_map = error_map

        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._last_output = None
        self._last_input = None
        self._last_error = None

        self.output_limits = output_limits
        self.output_pads = output_pads
        self.output_cutoffs = output_cutoffs
        self.reset()

    @micropython.native
    def __call__(self, input_, dt):
        """
        Update the PID controller.

        Call the PID controller with *input_* and calculate and return a control output if
        sample_time seconds has passed since the last update. If no new output is calculated,
        return the previous output instead (or None if no value has been calculated yet).

        :param dt: If set, uses this value for timestep instead of real time. This can be used in
            simulations when simulation time is different from real time.
        """
        """
        Обновите ПИД-регулятор.

        Вызовите ПИД-регулятор с *input_* и вычислите и верните управляющий вывод, если с момента
        последнего обновления прошло sample_time секунд. Если новый результат не вычисляется,
        вместо него верните предыдущий результат (или None, если значение еще не вычислено).

        :param dt: Если установлено, использует это значение для временного шага вместо реального времени.
            Это можно использовать в симуляциях, когда время симуляции отличается от реального времени.
         """
        if not self.auto_mode:
            return self._last_output

        if (self.sample_time is not None) and (dt < self.sample_time) and (self._last_output is not None):
            # only update every sample_time seconds
            return self._last_output

        # compute error terms
        error = self.setpoint - input_
        d_input = 0
        if self._last_input is not None:
            d_input = input_ - self._last_input

        # check if must map the error
        if self.error_map is not None:
            error = self.error_map(error)

        # compute the proportional term
        if self.Kp != 0:
            if not self.proportional_on_measurement:
                # regular proportional-on-error, simply set the proportional term
                self._proportional = self.Kp * error
            else:
                # add the proportional error on measurement to error_sum
                self._proportional -= self.Kp * d_input

        # compute integral and derivative terms
        if self.Ki != 0:
            self._integral += self.Ki * error * dt
            self._integral = _clamp(self._integral, self.output_limits)  # avoid integral windup

        self._derivative = -self.Kd * d_input / dt

        # compute final output
        output = self._proportional + self._integral + self._derivative
        output = _clamp(output, self.output_limits)
        output = _clamp_pad(output, self.output_pads)
        #output = _cutoffs(output, self.output_cutoffs)

        # keep track of state
        self._last_input = input_
        self._last_error = error
        self._last_output = output

        return output

    def prn(self):
        return 'setpoint={} last_input={} last_error={} last_output={} components={}'.format(self.setpoint, self._last_input, self._last_error, self._last_output, self.components)

    def __repr__(self):
        # yapf: disable
        return (
            '{}('
            'Kp={}, Ki={}, Kd={}, '
            'setpoint={}, sample_time={}, '
            'output_limits={}, '
            'output_pads={}, '
            'output_cutoffs={}, '
            'auto_mode={}, proportional_on_measurement={}, '
            'error_map={}, '
            'components={}'
            ')'
        ).format(self.__class__.__name__,
            self.Kp, self.Ki, self.Kd,
            self.setpoint, self.sample_time,
            self.output_limits,
            self.output_pads,
            self.output_cutoffs,
            self.auto_mode, self.proportional_on_measurement,
            self.error_map,
            self.components
        )
        # yapf: enable

    @property
    def components(self):
        """
        The P-, I- and D-terms from the last computation as separate components as a tuple. Useful
        for visualizing what the controller is doing or when tuning hard-to-tune systems.
        """
        """
        P-, I- и D-члены из последнего вычисления как отдельные компоненты как кортеж.
        Полезно для визуализации того, что делает контроллер, или при настройке трудно настраиваемых систем.
        """
        return self._proportional, self._integral, self._derivative

    @property
    def tunings(self):
        """The tunings used by the controller as a tuple: (Kp, Ki, Kd)."""
        return self.Kp, self.Ki, self.Kd

    @tunings.setter
    def tunings(self, tunings):
        """Set the PID tunings."""
        kP, kI, kD = tunings
        assert kP >= 0 and kI >= 0 and kD >= 0
        if self.direction == -1:
            self.Kp, self.Ki, self.Kd = -kP, -kI, -kD
        else:
            self.Kp, self.Ki, self.Kd = kP, kI, kD

    @property
    @micropython.native
    def auto_mode(self):
        """Whether the controller is currently enabled (in auto mode) or not."""
        return self._auto_mode

    @auto_mode.setter
    @micropython.native
    def auto_mode(self, enabled):
        """Enable or disable the PID controller."""
        self.set_auto_mode(enabled)

    def set_auto_mode(self, enabled, last_output=None):
        """
        Enable or disable the PID controller, optionally setting the last output value.

        This is useful if some system has been manually controlled and if the PID should take over.
        In that case, disable the PID by setting auto mode to False and later when the PID should
        be turned back on, pass the last output variable (the control variable) and it will be set
        as the starting I-term when the PID is set to auto mode.

        :param enabled: Whether auto mode should be enabled, True or False
        :param last_output: The last output, or the control variable, that the PID should start
            from when going from manual mode to auto mode. Has no effect if the PID is already in
            auto mode.
        """
        """
        Включение или отключение ПИД-регулятора, при необходимости устанавливая последнее выходное значение.

        Это полезно, если некоторая система управлялась вручную и должен действовать PID.
        В этом случае отключите PID, установив автоматический режим на False, а затем,
        когда PID должен быть снова включен, передайте последнюю выходную переменную (управляющую переменную),
        и она будет установлена как начальный I-член, когда PID установлен в автоматический режим.
        :param enabled: должен ли быть включен автоматический режим, True или False
        :param last_output: Последний выход или управляющая переменная, с которой должен запускаться PID
            при переходе из ручного режима в автоматический. Не действует, если PID уже находится в автоматическом режиме.
        """
        if enabled and not self._auto_mode:
            # switching from manual mode to auto, reset
            self.reset()

            self._integral = last_output if (last_output is not None) else 0
            self._integral = _clamp(self._integral, self.output_limits)

        self._auto_mode = enabled

    @property
    @micropython.native
    def output_limits(self):
        """
        The current output limits as a 2-tuple: (lower, upper).

        See also the *output_limits* parameter in :meth:`PID.__init__`.
        """
        return self._min_output, self._max_output

    @output_limits.setter
    @micropython.native
    def output_limits(self, limits):
        """Set the output limits."""
        if limits is None:
            self._min_output, self._max_output = None, None
            return

        min_output, max_output = limits

        if (None not in limits) and (max_output < min_output):
            raise ValueError('lower limit must be less than upper limit')

        self._min_output = min_output
        self._max_output = max_output

        self._integral = _clamp(self._integral, self.output_limits)
        self._last_output = _clamp(self._last_output, self.output_limits)

    def reset(self):
        """
        Reset the PID controller internals.

        This sets each term to 0 as well as clearing the integral, the last output and the last
        input (derivative calculation).
        """
        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._integral = _clamp(self._integral, self.output_limits)

        self._last_output = None
        self._last_input = None

    @micropython.native
    def setDirection(self, direction):
        """    # Set direction """
        assert (direction == -1) or (direction == 1)
        if direction != self.direction:
            self.kP = -self.kP
            self.kI = -self.kI
            self.kD = -self.kD
            self.direction = direction
