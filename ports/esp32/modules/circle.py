from gc import collect
collect()
from math import pi, cos, sin  # degrees,
collect()
from Owl_API import value_sub  # value_cmp,
collect()

CIRCLE_ANGLE = 2.5  # 10  # угол отклонения оси антенны (должен быть меньше или равен углу направленности антенны)
CIRCLE_RANGE = 36  # 8  # 12  # количество точек на окружности
circle = []  # [[azim, elev, value],]  # список[CIRCLE_RANGE] позиций и значений в позициях
circle_a = 0  # условный центр окружности
circle_e = 0  # условный центр окружности
circle_i = 0  # текущая точка на окружности
circle_pos = 0  # стартовая точка на окружности


def calc_circle(a, e):
    global circle

    for i in range(CIRCLE_RANGE):
        rad = 2 * pi * i / CIRCLE_RANGE
        circle[i][0] = round(a + CIRCLE_ANGLE * cos(rad), 1)
        circle[i][1] = round(e - CIRCLE_ANGLE * sin(rad), 1)


def init_circle(a, e):
    global circle, circle_a, circle_e, circle_i, circle_pos

    circle_a = a
    circle_e = e
    circle_pos = 0
    circle = [[0, 0, {}] for _ in range(CIRCLE_RANGE)]
    calc_circle(a, e)
    #print('circle=', circle)


def handle_circle(owl, a, e, ros_params):
    global circle, circle_a, circle_e, circle_i, circle_pos

    if owl.azim.mover.is_ready() and owl.elev.mover.is_ready():
        circle[circle_i][2] = owl.value_now
        #print('owl.value_now', owl.value_now)
        circle_i += 1
        if circle_i >= CIRCLE_RANGE:
            circle_i = 0

        if circle_i == circle_pos:
            #print('Circle=', circle)
            r = CIRCLE_RANGE // 2
            circle_sub = [0 for _ in range(r)]
            for j in range(r):
                circle_sub[j] = value_sub(circle[j][2], circle[j + r][2], ros_params)
            max_sub = -99999999
            max_j = -1
            for j in range(r):
                if max_sub < circle_sub[j]:
                    max_sub = circle_sub[j]
                    max_j = j
            if (max_j != -1) and (max_sub > 0):
                print('circle_sub', circle_sub)
                print('max_j, circle_pos', max_j, circle_pos)
                print('a, e', a, e)
                circle_pos = max_j
                a += circle[max_j][0]
                e += circle[max_j][1]
                print('a, e', a, e)
                owl.azim.mover.angle(a)
                owl.elev.mover.angle(e)
                calc_circle(a, e)
        else:
            owl.azim.mover.angle(circle[circle_i][0])
            owl.elev.mover.angle(circle[circle_i][1])
