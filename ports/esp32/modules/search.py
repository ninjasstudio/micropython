from Owl_API import value_cmp, value_sub, calc_angles, handle_ros_command, print_motor

SEARCH_LEVEL_DIFFERENCE = 10  # dB
ROS_LOST = 5


def handle_search(owl, motor, ros_params):
    # Поиск середины плато или максимума на плато диагаммы уровня сигнала.
    def set(a, v):
        if motor.search_dir > 0:
            motor.angle_plus = a
            motor.value_plus = v
        else:
            motor.angle_minus = a
            motor.value_minus = v
    #end set()
    
    if motor.state_prev != motor.state:
        motor.state_prev = motor.state
        #if motor.state == 0:
        #    print("")
        #    print(motor.mover.name, "owl.mode", owl.mode)
        print("motor.state, motor.state2", motor.state)  # , motor.state2

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
            owl.mode = owl.MD_SECTOR_A
        return
    owl.lost = 0
    
    owl.filter_append(v)
    if motor.state in (3, 4):
        owl.angle_diagram_append(a, v)

    if len(v) != 0:
        if len(motor.value_start) == 0:
            motor.value_start = v
            motor.angle_start = a  # обнаружен сигнал в этой позиции
        if value_cmp(v, motor.value_best, ros_params) > 0:
            # нашли "лучше"
            motor.angle_best = a
            motor.value_best = v
            if motor.angle_best is None:
                owl.s1 = "Found"
                print(owl.s1)
            print("best", motor.angle_best, motor.value_best)
        owl.lost = 0
    else:
        if motor.angle_best is not None:
            owl.lost += 1
            if owl.s1 != "Lost":
                owl.s1 = "Lost"
                print(owl.s1)

    if motor.state == 0:  # очищаем исходные
        motor.angle_start = a  # если сигнал отсутствует, то стартовая позиция будет переписана при обнаружении сигнала
        motor.value_start = v
        
        owl.angle_diagram_clear()
        owl.filter_clear()
        motor.angle_minus = None
        motor.angle_plus = None
        motor.avg_start = {}
        motor.search_dir = motor.search_dir_next
        motor.search_dir_next = -motor.search_dir_next
        print('motor.search_dir_next', motor.mover.name, motor.search_dir_next)
        motor.state = 11
        
    elif motor.state == 11:  # попытка заполнить фильтр
        if len(v) == 0:  # не ждем, не будет использоваться
            motor.state = 12
        elif owl.filter_is_full():  # ждем заполнения фильтра, фиксируем исходные
            motor.angle_start = a
            motor.value_start = v
            motor.avg_start = owl.filter_avg()
            motor.state = 12
            
    elif motor.state == 12:  # даем задание в "плюсовом" направлении на всю ширину
        #print("motor.angle_start, motor.value_start, motor.avg_start", motor.angle_start, motor.value_start, motor.avg_start)
        if motor.search_dir > 0:
            motor.angle(motor.max_search)
        else:
            motor.angle(motor.min_search)
        motor.state = 1
        
    elif motor.state == 1:
        if len(v) == 0:
            motor.state2 = 0  # 0-поиск "вправо до упора", 1-поиск "влево до упора", 2-прошли полный цикл-слежение по уровню SEARCH_LEVEL_DIFFERENCE
            motor.angle_best = None
            motor.value_best = {}
        else:
            motor.state2 = 2  # 2-слежение по уровню SEARCH_LEVEL_DIFFERENCE
            motor.angle_best = a
            motor.value_best = v
        motor.avg_best = {} 
        motor.state = 2
        
    elif motor.state == 2:  # нахождение "правой" границы
        sub = value_sub(motor.value_best, v, ros_params)
        if (sub >= SEARCH_LEVEL_DIFFERENCE) and (motor.state2 == 2)\
        or (len(motor.value_best) > 0) and (len(v) == 0) and (owl.lost > ROS_LOST) \
        or motor.mover.is_ready() \
        or (motor.search_dir < 0) and (a <= motor.min_search) \
        or (motor.search_dir > 0) and (a >= motor.max_search):
            motor.mover.stop_move()
            print("2. best, best.a, v, a, sub, motor.mover.is_ready(), motor.search_dir, motor.min_search, motor.max_search", motor.value_best, motor.angle_best, v, a, sub, motor.mover.is_ready(), motor.search_dir, motor.min_search, motor.max_search)
            set(a, v)
            #reverse
            owl.angle_diagram_clear()
            motor.avg_bisector_diff = {}
            motor.avg_bisector_max = {}

            motor.search_dir = -motor.search_dir
            if motor.search_dir > 0:
                motor.angle(motor.max_search)
            else:
                motor.angle(motor.min_search)
            motor.state = 3
    elif motor.state == 3:  # пропуск стартовой позиции # собираем ros_params данные в таблицу
        a = motor.mover.angle_now()  # перечитываем для точности
        if (motor.search_dir < 0) and ((a <= motor.angle_start) or (a <= motor.min_search)) \
        or (motor.search_dir > 0) and ((a >= motor.angle_start) or (a >= motor.max_search)) \
        or motor.mover.is_ready():
            motor.state = 4
    elif motor.state == 4:  # нахождение "левой" границы # собираем ros_params данные в таблицу
        sub = value_sub(motor.value_best, v, ros_params)
        if (sub >= SEARCH_LEVEL_DIFFERENCE) and (motor.state2 == 2) \
        or (len(v) == 0) and (motor.state2 == 2) \
        or (len(motor.value_best) > 0) and (len(v) == 0) and (owl.lost > ROS_LOST) \
        or motor.mover.is_ready() \
        or (motor.search_dir < 0) and (a <= motor.min_search) \
        or (motor.search_dir > 0) and (a >= motor.max_search):  
            motor.mover.stop_move()
            #print("best4, v, a, sub", motor.value_best, v, a, sub)
            print("4. best, best.a, v, a, sub, motor.mover.is_ready(), motor.search_dir, motor.min_search, motor.max_search", motor.value_best, motor.angle_best, v, a, sub, motor.mover.is_ready(), motor.search_dir, motor.min_search, motor.max_search)
            set(a, v)
            if len(motor.value_best) > 0:
                if calc_angles(owl, motor):
                    if motor.angle_bisector_diff is not None:
                        motor.angle(motor.angle_bisector_diff)  # даем задание на перемещение в середину плато
                        motor.state = 51
                            
                    else:
                        motor.angle(motor.angle_bisector_max)  # даем задание на перемещение в середину max
                        motor.state = 54
                else:
                    motor.angle(motor.angle_best)  # нет данных, попробуем в позиции angle_best
                    motor.state = 57
            else:
                motor.angle(motor.angle_start)  # даем задание на перемещение в исходную позицию
                
            motor.state = 6
#             else:
#                 print("Нет сигнала, повторный поиск")
#                 motor.state = 12

    elif motor.state == 51:  # даем задание на перемещение в середину плато
        motor.angle(motor.angle_bisector_diff)
        motor.state = 52
    elif motor.state == 52:  # идем в середину плато
        if motor.mover.is_ready():
            owl.filter_clear()
            motor.state = 53
    elif motor.state == 53:
        if len(v) == 0:
            motor.state = 54
        elif owl.filter_is_full():  # ждем заполнения фильтра, фиксируем среднее значение в серединe плато
            motor.avg_bisector_diff = owl.filter_avg()
            motor.state = 54

    elif motor.state == 54:  # даем задание на перемещение в середину max
        motor.angle(motor.angle_bisector_max)
        motor.state = 55
    elif motor.state == 55:  # идем в середину max
        if motor.mover.is_ready():
            owl.filter_clear()
            motor.state = 56
    elif motor.state == 56:
        if len(v) == 0:
            motor.state = 57
        elif owl.filter_is_full():  # ждем заполнения фильтра, фиксируем среднее значение в середине max
            motor.avg_bisector_max = owl.filter_avg()
            motor.state = 57

    elif motor.state == 57:  # даем задание на перемещение в лучшую позицию
        motor.angle(motor.angle_best)
        motor.state = 58
    elif motor.state == 58:  # идем в лучшую позицию
        if motor.mover.is_ready():
            owl.filter_clear()
            motor.state = 59
    elif motor.state == 59:
#         if len(v) == 0:
#             print("Отключился сигнал, повторный поиск")
#             motor.state = 1
#         el
        if owl.filter_is_full():  # ждем заполнения фильтра, фиксируем среднее значение в лучшей позиции
            motor.avg_best = owl.filter_avg()

            #                 avg_list = [motor.avg_best, motor.avg_bisector_diff, motor.avg_bisector_max, motor.avg_start]
            #                 print(avg_list)
            #                 avg_list.sort(key=value_cmp)
            #                 print(avg_list)
            if value_cmp(motor.avg_bisector_max, motor.avg_best, ros_params) > 0:
                if value_cmp(motor.avg_bisector_max, motor.avg_bisector_diff, ros_params) > 0:
                    if value_cmp(motor.avg_bisector_max, motor.avg_start, ros_params) > 0:
                        motor.angle(motor.angle_bisector_max)  # даем задание на перемещение в середину max
            elif value_cmp(motor.avg_bisector_diff, motor.avg_best, ros_params) > 0:
                if value_cmp(motor.avg_bisector_diff, motor.avg_bisector_max, ros_params) > 0:
                    if value_cmp(motor.avg_bisector_diff, motor.avg_start, ros_params) > 0:
                        motor.angle(motor.angle_bisector_diff)  # даем задание на перемещение в середину плато
            else:                        
                motor.angle(motor.angle_start)  # даем задание на перемещение в исходную позицию
            '''    
            elif value_cmp(motor.avg_start, motor.avg_best, ros_params) > 0:
                if value_cmp(motor.avg_start, motor.avg_bisector_max, ros_params) > 0:
                    if value_cmp(motor.avg_start, motor.avg_bisector_diff, ros_params) > 0:
                        motor.angle(motor.angle_start)  # даем задание на перемещение в исходную позицию
            ' ' '
                    if value_cmp(motor.avg_bisector_diff, motor.avg_bisector_max, ros_params) > 0:
                        if value_cmp(motor.avg_bisector_diff, motor.avg_start, ros_params) > 0:
                            motor.angle(motor.angle_bisector_diff) # даем задание на перемещение в середину плато
                        else:
                            motor.angle(motor.angle_start) # даем задание на перемещение в исходную позицию
                else:
                    else:
                        if value_cmp(motor.avg_bisector_max, motor.avg_start, ros_params) < 0:
                            motor.angle(motor.angle_start) # даем задание на перемещение в исходную позицию
                '''
            motor.state = 6
    elif motor.state == 6:
        if motor.mover.is_ready():
            print_motor(owl, motor, a, v)

            motor.state = 0
            if owl.mode == owl.MD_SEARCH_A:
                if motor.angle_best is None:
                    owl.elev.search_dir = -owl.elev.search_dir
                    owl.elev.angle(owl.elev.angle_start + owl.elev.search_dir * owl.ANTENNA_ANGLE)
                else:
                    owl.mode = owl.MD_SEARCH_E
            elif owl.mode == owl.MD_SEARCH_E:
                owl.mode = owl.MD_SEARCH_A
                owl.mode = owl.MD_ESCORT_A

            if owl.mode in (owl.MD_SEARCH_A, owl.MD_SEARCH_E):
                owl.angle_diagram_clear()
                
    else:
        raise
