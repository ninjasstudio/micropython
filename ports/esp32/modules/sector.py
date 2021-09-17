# sector.py
from utime import time

from Owl_API import value_cmp, handle_ros_command, print_motor

import config_version


def handle_sector(owl, motor, ros_params):
    if config_version.HARDWARE == 2:
        if owl.mode == owl.MD_SECTOR_E:
            owl.mode = owl.MD_COMMUNICATE
    
    # Поиск глобального максимального уровня в секторе.
    if motor.state_prev != motor.state:
        motor.state_prev = motor.state
        print("motor.state", motor.state)

    handle_ros_command(owl)
    v = owl.value_now
    if motor.mover.name[0] == 'A':
        a = owl.azim_angle_now
    else:
        a = owl.elev_angle_now
    a = round(a, 1)

    if len(v):
        if len(motor.value_start) == 0:
            motor.value_start = v  # обнаружен сигнал  
            motor.angle_start = a  # в этой позиции
        if value_cmp(v, motor.value_best, ros_params) > 0:
            motor.value_best = v  # нашли "лучше" уровень сигнала
            motor.angle_best = a  # в этой позиции

    if motor.state == 0:  # очищаем исходные
        owl.sector_time = time()
        ros_command = ["/interface/wireless/set", "=.id=wlan1", "=tx-chains=0,1", "=rx-chains=0,1"]
        owl.ros_command2 = ros_command
        
        owl.sector_counter = 0
        if (a >= motor.max_search):
            motor.search_dir = -1
            owl.sector_counter = 1
        elif (a <= motor.min_search):
            motor.search_dir = 1
            owl.sector_counter = 1
        
        if owl.mode == owl.MD_SECTOR_A:
            owl.value_start_azim = v
        owl.elev.angle_start = owl.elev.mover.angle_now()
        if len(v):
            motor.angle_best = a
            motor.value_best = v
        else:
            ### owl.elev.angle(0) лучше разрешить поиск из ручной позиции, а затем перейти в горизонт
            motor.angle_best = None
            motor.value_best = {}

        motor.angle_start = a  # если сигнал отсутствует, то стартовая позиция будет переписана при обнаружении сигнала
        motor.value_start = v
        motor.value_begin = v  # сигнал в начале поиска, не будет перезаписан
        motor.angle_begin = a
        
        #motor.state2 = 0  # 0-поиск "вправо до границы сектора", 1-поиск "влево до границы сектора"
        motor.state = 2

    elif motor.state == 2:
        # даем задание на всю ширину
        if motor.search_dir > 0:
            motor.angle(motor.max_search)
        else:
            motor.angle(motor.min_search)
        motor.state = 3

    elif motor.state == 3:
        # проверяем достижение границ сектора
        if motor.mover.is_ready() \
        or (motor.search_dir > 0) and (a >= motor.max_search) \
        or (motor.search_dir < 0) and (a <= motor.min_search):
            motor.mover.stop_move()
            if (len(motor.value_begin) == 0) and (len(v) != 0):
                motor.value_begin = v
                owl.sector_counter = 0  # впервые обнаружен сигнал, нужно пройти полный сектор поиска
                
            owl.sector_counter += 1
            if 0 and (owl.state == owl.CM_NO) and (len(motor.value_start) != 0):
                # motor.mover.stop_move()  #
                motor.angle(motor.angle_start)
                motor.state = 35
            elif owl.sector_counter < 2:
                motor.search_dir = -motor.search_dir
                motor.state = 2  # повторный поиска в противоположном направлении, нужно пройти полный сектор поиска
            else:
                if motor.angle_best is not None:
                    motor.angle(motor.angle_best)  # идем в лучшее
                    motor.state = 5
                else:
                    # motor.angle(motor.angle_start)  # возвращаемся в исходное
                    motor.mover.stop_move()  # отсутствует сигнал во всем секторе, нет смысла возвращаться в исходное
                    motor.state = 8  # лучше перепозиционировать угол места

    elif motor.state == 35:
        if motor.mover.is_ready():
            motor.mover.stop_move()
            motor.state = 4
    elif motor.state == 4:
        if owl.state == owl.CM_NO:
            motor.mover.stop_move()
            if (len(v) != 0):
                owl.state = owl.CM_SEE
                owl.azim.mover.pid.output_limits = owl.azim_output_limits # восстановить скорость
            else:                
                motor.search_dir = -motor.search_dir
                motor.state = 2  # нет сигнала, переискать
        elif owl.state == owl.CM_SECTOR:
            motor.state = 2  # увидели корреспондента, переискать
        
    elif motor.state == 5:
        # ожидание позиционирования
        if motor.angle_best is not None:
            if motor.angle_best != motor.mover.angle_target():
                motor.angle(motor.angle_best)  # если по пути найдется еще лучше, то выбираем его
        if motor.mover.is_ready():
            motor.mover.stop_move()
            motor.state = 8
                
    elif motor.state == 8:
        motor.mover.stop_move()
        print_motor(owl, motor, a, v)

        if (motor.angle_best is None) or (len(v) == 0):  # сигнал отствовал или потерялся
            # повторить обзор азиимута сместив угол места
            if owl.elev.angle_best is not None:
                # сигнал изначально где-то присутствовал, но потерялся
                owl.elev.angle(owl.elev.angle_best)  # один проход по лучшему предыдущему углу места
                owl.elev.angle_best = None
                owl.sector_counter = 0
            elif owl.elev.angle_start != 0:        
                owl.elev.angle_start = 0
                owl.elev.angle(0)  # один проход по горизонту в угле места
                owl.sector_counter = 0
            else:
                # двойной угол луча антенны
                owl.elev.search_dir = -owl.elev.search_dir  # попеременно
                owl.elev.angle(owl.elev.angle_start + owl.elev.search_dir * owl.ANTENNA_ANGLE)
                if owl.sector_counter > 3:
                    owl.sector_counter = 0

            if motor.angle_best is not None:
                if motor.angle_best > motor.angle_start:
                    motor.search_dir = 1
                elif motor.angle_best < motor.angle_start:
                    motor.search_dir = -1
                else:    
                    motor.search_dir = -motor.search_dir  # следующий цикл поиска в противоположном направлении
            
            owl.mode = owl.MD_SECTOR_A  # переключиться на азимут при отсутствии или потере сигнала
            #motor.state2 = 0
            motor.state = 2
        else:
            if owl.mode == owl.MD_SECTOR_A:
                owl.mode = owl.MD_SECTOR_E  # переключение на угол места
            elif len(owl.value_start_azim) == 0:
                # сигнал обнаружен в секторе угла места
                owl.mode = owl.MD_SECTOR_A  # переключение на азимут
            else:
                owl.mode = owl.MD_ESCORT_A  # переключение на режим слежения
                owl.corr.out = "ID\n"
                owl.mode = owl.MD_COMMUNICATE
#         if owl.mode == owl.MD_ESCORT_A:        
#             ros_command = ["/interface/wireless/set", "=.id=wlan1", "=tx-chains=0", "=rx-chains=0"]
#             owl.ros_command2 = ros_command
            
    else:
        raise
