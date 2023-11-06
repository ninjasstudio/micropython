# escort.py
from Owl_API import value_cmp, handle_ros_command, print_motor


def handle_escort(owl, motor, ros_params):
    # Движение ++/-- пока мгновенный уровень сигнала не ниже, чем исходный уровень(поиск локального максимального уровня).
    # При потере сигнала переход на поиск в секторе не производится, ждем +/- в этой точке.
    # Изначально сигнал может отсутствовать. 
    handle_ros_command(owl)
    if owl.value_now is None:
        return
    v = owl.value_now
    if owl.mode == owl.MD_ESCORT_A:
        a = owl.azim_angle_now
    else:
        a = owl.elev_angle_now
    a = round(a, 1)

    if len(v) > 0:
        if len(motor.value_start) == 0:
            motor.value_start = v  # обнаружен сигнал
            motor.angle_start = a  # в этой позиции
            
    if motor.state == 0:  # очищаем исходные
        if owl.mode == owl.MD_ESCORT_A:
            owl.ros_command2 = ["/system/script/run", "=.id=communication"]
        if len(v):
            motor.angle_best = a
            owl.ros_best = v

        motor.angle_start = a  # если сигнал отсутствует, то стартовая позиция будет переписана при обнаружении сигнала
        motor.value_start = v
        motor.state = 2

    elif motor.state == 2:
        # даем задание на ширину луча антенны
        if motor.search_dir > 0:
            motor.angle_target = motor.angle_start + owl.ANTENNA_ANGLE
        else:
            motor.angle_target = motor.angle_start - owl.ANTENNA_ANGLE
        # motor.angle_target = round(motor.angle_target, 1)
        motor.state = 3

    elif motor.state == 3:
        # сравнение мгновенных значений
        cmp = value_cmp(v, motor.value_start, ros_params)
        if cmp < 0:
            motor.mover.stop()
            motor.state = 5
        # продолжаем движение в том же направлении

        # проверяем достижения задания или упора
        if motor.mover.is_ready() \
        or (motor.search_dir > 0) and (a >= motor.max_search) \
        or (motor.search_dir < 0) and (a <= motor.min_search):
            motor.mover.stop()
            motor.state = 5

    elif motor.state == 5:
        if motor.angle_best is not None:
            # идем в лучшее
            motor.angle_target = motor.angle_best
            if motor.angle_best > motor.angle_start:
                motor.search_dir = 1
            elif motor.angle_best < motor.angle_start:
                motor.search_dir = -1
            else:
                motor.search_dir = -motor.search_dir  # следующий цикл поиска в противоположном направлении
        else:
            # возвращаемся в исходное
            motor.angle_target = motor.angle_start
            motor.search_dir = -motor.search_dir  # следующий цикл поиска в противоположном направлении
        motor.state = 8

    elif motor.state == 8:
        # ожидание позиционирования
        if motor.angle_best is not None:
            # если по пути найдется еще лучше, то выбираем его
            motor.angle_target = motor.angle_best

        if motor.mover.is_ready():
            motor.mover.stop()
            print_motor(owl, motor, a, v)

            # переключение на другой мотор
            if owl.mode == owl.MD_ESCORT_A:
                owl.mode = owl.MD_ESCORT_E
            else:
                owl.mode = owl.MD_ESCORT_A

    else:
        raise
