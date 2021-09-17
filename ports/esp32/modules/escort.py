# escort.py
from Owl_API import value_cmp, handle_ros_command, print_motor


def handle_escort(owl, motor, ros_params):
    # Движение ++/-- пока мгновенный уровень сигнала не ниже, чем исходный уровень(поиск локального максимального уровня).
    # При потере сигнала переход на поиск в секторе.
    ### Изначально сигнал может отсутствовать. Тогда поиск в полном диапазоне(min_search, max_search),
    ### осуществится поиск максимального уровня.
    if motor.state_prev != motor.state:
        motor.state_prev = motor.state
        #if motor.state == 0:
        #    print("")
        #    print(motor.mover.name, "owl.mode", owl.mode)
        print("motor.state", motor.state)

    handle_ros_command(owl)
    v = owl.value_now
    if motor.mover.name[0] == 'A':
        a = owl.azim_angle_now
    else:
        a = owl.elev_angle_now
    a = round(a, 1)

    if len(v) == 0:
        owl.lost += 1    
        if owl.lost > owl.LOSTS:
            print('losts', owl.lost)
            owl.mode = owl.MD_SECTOR_A
        return
    owl.lost = 0
    
    if len(motor.value_start) == 0:
        motor.value_start = v
        motor.angle_start = a  # обнаружен сигнал в этой позиции
    if value_cmp(v, motor.value_best, ros_params) > 0:
        # нашли "лучше"
        motor.angle_best = a
        motor.value_best = v

    if motor.state == 0:  # очищаем исходные
        if owl.mode == owl.MD_ESCORT_A:
            ros_command = ["/interface/wireless/set", "=.id=wlan1", "=tx-chains=0", "=rx-chains=0"]
            owl.ros_command2 = ros_command
        if len(v) == 0:
            motor.angle_best = None
            motor.value_best = {}
            motor.state2 = 0  # 0-поиск "вправо до упора", 1-поиск "влево до упора", 2-прошли полный цикл-слежение по уровню
        else:
            motor.angle_best = a
            motor.value_best = v
            '''
            if owl.mode_before in (owl.MD_ESCORT_A,):
                #print("owl.mode, owl.mode_before, motor.state2", owl.mode, owl.mode_before, motor.state2, owl.azim.state2)
                if owl.azim.state2 != 2:
                    motor.state2 = 0  # 0-поиск "вправо до упора", 1-поиск "влево до упора", 2-прошли полный цикл-слежение по уровню
                else:
                    motor.state2 = 2  # 2-слежение по уровню
            elif owl.mode_before in (owl.MD_ESCORT_E, owl.MD_SEARCH_E):
                motor.state2 = 2  # 2-слежение по уровню
            else:
                motor.state2 = 0  # 0-поиск "вправо до упора", 1-поиск "влево до упора", 2-прошли полный цикл-слежение по уровню
            '''    
            motor.state2 = 2  # 2-слежение по уровню

        motor.angle_start = a  # если сигнал отсутствует, то стартовая позиция будет переписана при обнаружении сигнала
        motor.value_start = v
        motor.state = 2

    elif motor.state == 2:
        if motor.state2 == 2:  # 2-слежение по уровню
            # даем задание на ширину луча антенны
            if motor.search_dir > 0:
                motor.angle(motor.angle_start + owl.ANTENNA_ANGLE)
            else:
                motor.angle(motor.angle_start - owl.ANTENNA_ANGLE)
        else:
            # даем задание на всю ширину
            if motor.search_dir > 0:
                motor.angle(motor.max_search)
            else:
                motor.angle(motor.min_search)
        motor.state = 3

    elif motor.state == 3:
        # сравнение мгновенных значений
        cmp = value_cmp(v, motor.value_start, ros_params)
        if (cmp < 0) and (motor.state2 == 2):
            motor.mover.stop_move()
            motor.state = 5
        # продолжаем движение в том же направлении

        # проверяем достижения упора
        if motor.mover.is_ready() \
        or (motor.search_dir > 0) and (a >= motor.max_search) \
        or (motor.search_dir < 0) and (a <= motor.min_search):
            motor.mover.stop_move()
            if motor.state2 == 0:
                motor.state2 = 1
                motor.search_dir = -motor.search_dir  # следующий цикл поиска в противоположном направлении
                motor.state = 2
            else:
                motor.state = 5

    elif motor.state == 5:
        if motor.angle_best is not None:
            # идем в лучшее
            motor.angle(motor.angle_best)
            if motor.angle_best > motor.angle_start:
                motor.search_dir = 1
            elif motor.angle_best < motor.angle_start:
                motor.search_dir = -1
            else:    
                motor.search_dir = -motor.search_dir  # следующий цикл поиска в противоположном направлении
        else:
            # возвращаемся в исходное
            motor.angle(motor.angle_start)
            motor.search_dir = -motor.search_dir  # следующий цикл поиска в противоположном направлении
        motor.state = 8

    elif motor.state == 8:
        # ожидание позиционирования
        if motor.angle_best is not None:
            if motor.angle_best != motor.mover.angle_target():
                # если по пути найдется еще лучше, то выбираем его
                motor.angle(motor.angle_best)
                
        if motor.mover.is_ready():
            motor.mover.stop_move()
            print_motor(owl, motor, a, v)
            
            # переключение на другой мотор
            if owl.mode == owl.MD_ESCORT_A:
                owl.mode = owl.MD_ESCORT_E  
            else:
                owl.mode = owl.MD_ESCORT_A

    else:
        raise
