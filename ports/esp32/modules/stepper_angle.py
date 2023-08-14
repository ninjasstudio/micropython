from stepper import Stepper
from steps_per_rev import StepsPerRev

class StepperAngle(Stepper, StepsPerRev):
    def __init__(self, name, pin_step, pin_dir, freq=1000, reverse_direction=0, max_limit=180, min_limit=-180, steps_per_rev=1):
        super().__init__(name, pin_step, pin_dir, freq, reverse_direction)
        
        self.max_limit = max_limit  # физические механические ограничения конструкции
        self.min_limit = min_limit
        
        self.steps_per_rev = steps_per_rev  # для StepsPerRev

    def __repr__(self):
        return f"StepperAngle(max_limit={self.max_limit}, min_limit={self.min_limit}, steps_per_rev={self.steps_per_rev}):" + super().__repr__()

    #@micropython.native
    @property
    def angle_now(self):
        return self.steps_to_angle(self.steps_now)

    #@micropython.native
    @property
    def angle_target(self):
        # print(f'{self.name} StepperAngle():angle_target.property')
        return self.steps_to_angle(self._steps_target)

    @angle_target.setter
    def angle_target(self, angle_target):
        # Set the target position that will be executed in the main loop
        # print(f'{self.name} StepperAngle():angle_target.setter angle_target={angle_target}')
        if angle_target > self.max_limit:
            self.steps_target = self.angle_to_steps(self.max_limit)
        elif angle_target < self.min_limit:
            self.steps_target = self.angle_to_steps(self.min_limit)
        else:    
            self.steps_target = self.angle_to_steps(angle_target)

    @property
    def rps(self):
        return self.f_to_rps(self._freq())

    @property
    def rpm(self):
        return self.f_to_rpm(self._freq())
