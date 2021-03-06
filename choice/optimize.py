﻿#!/usr/bin/python
# -*- coding: utf-8 -*-

# External imports
from copy import deepcopy
import math, random
from sys import maxsize

# Internal imports
from calculate_TcTeMem import calculate_abs_values
import global_vars as gl
import par
import smooth_stat as sm
import stat_adaptation as stat

# Хранить в оперативной памяти, вычисленные на предыдущих шагах оптимизации распределения? {True, False}
DISTRIBUTION_DATABASE = True

# Начальное значение температуры
START_TEMPERATURE = 0.5 # Range of temperature: (0, 1].


# Закон убывания температуры: 0, 1, 2
# 0 -> 1/ln(n)
# 1 -> 1/n
# 2 -> alpha^n
TEMPERATURE_LAW_TYPE = 2
# значение alpha
ALPHA_IN_TEPMERATURE_LAW = 0.7

#def change_var(newvalue):
    #global ALPHA_IN_TEPMERATURE_LAW
    #ALPHA_IN_TEPMERATURE_LAW = newvalue

def temperature_law(i):
    if TEMPERATURE_LAW_TYPE == 0:
        return 1. / math.log(i + 1)
    elif TEMPERATURE_LAW_TYPE == 1:
        return 1. / i
    elif TEMPERATURE_LAW_TYPE == 2:
        return ALPHA_IN_TEPMERATURE_LAW ** i

def temperature(i):
    '''Функция вычисляет значение температуры на итерации i
       i = 1, 2, ... '''
    koef = START_TEMPERATURE / temperature_law(1)
    return koef * temperature_law(i)

# 
def distribution(T):
    '''Вероятностное распределение, определяющее выбор следующего состояния системы в зависимости от ее текущих состояния и температуры'''
    # return random.gauss(0, T) # нормальное распределение
    return random.choice([-1, 1]) * T * ((1 + 1./T) ** abs(2 * random.uniform(-0.5, 0.5)) - 1) # распределение для сверхбыстрого отжига
    #return T * math.tan(math.pi * random.uniform(-0.5, 0.5)) # распределение Коши
    #return math.sqrt(T * 3) * random.uniform(-1, 1) # равномерное распределение

KOEF_TIME_EXEC_IMPOTANCE = 5

MAX_NUMBER_ITERATIONS = 10
MAX_NUMBER_OF_ATTEMPTS_FOR_ITERATION = 10
# Уменьшать значение температуры после итераций, на которых не был осуществлен переход к лучшему значению
DECREASE_TEMPERATURE_BEFORE_UNFORTUNATE_ITERATIONS = True

            
def F(list_trio):
    len_list_trio = len(list_trio)
    if len_list_trio == 0:
        raise BaseException('list_trio is empty')
    
    mul_delta_T_comp = 1
    mul_delta_T_exec = 1
    mul_delta_V = 1
    for trio in list_trio:
        delta_T_comp = trio[0]
        if delta_T_comp > 1.25:
            return maxsize
        mul_delta_T_comp *= delta_T_comp
        
        delta_T_exec = trio[1]
        if delta_T_exec > 1.05:
            return maxsize
        mul_delta_T_exec *= delta_T_exec
        
        delta_V = trio[2]
        if delta_V > 1.5:
            return maxsize
        mul_delta_V *= delta_V
    
    mul_delta_T_exec = mul_delta_T_exec ** (1. / len_list_trio)
    mul_delta_T_comp = mul_delta_T_comp ** (1. / len_list_trio)
    mul_delta_V = mul_delta_V ** (1. / len_list_trio)
        
    return KOEF_TIME_EXEC_IMPOTANCE * mul_delta_T_exec + mul_delta_T_comp + mul_delta_V

def calculate_F(values, values_default):
    list_rel_trio = []
    for key in values.iterkeys():
        trio = values[key]
        trio_default = values_default[key]
        rel_trio = (trio[0] / trio_default[0], trio[1] / trio_default[1], trio[2] / trio_default[2])
        list_rel_trio.append(rel_trio)
    return F(list_rel_trio)

def condition(x_list, coord, old_pv_list, new_pv_list, index_0_flag, index_1_flag):
    if index_0_flag:
        parname = par.reg_seq[0]
        x = x_list[0]
        if not (par.cond[parname](x, old_pv_list[0]) and par.cond[parname](x, new_pv_list[0])):
            return False
    if index_1_flag:
        parname = par.reg_seq[1]
        x = x_list[1]
        if not (par.cond[parname](x, old_pv_list[1]) and par.cond[parname](x, new_pv_list[1])):
            return False
    for i in xrange(2, coord):
        parname = par.reg_seq[i]
        x = x_list[i]
        if not (par.cond[parname](x, old_pv_list[i]) and par.cond[parname](x, new_pv_list[i])):
            return False
    return True

def icv_condition(x_list, coord, old_pv_list, new_pv_list):
    for i in xrange(coord):
        parname = par.icv_seq[i]
        x = x_list[i]
        if not (par.cond[parname](x, old_pv_list[i]) and par.cond[parname](x, new_pv_list[i])):
            return False
    return True
    

def shift(par_list, max_sum, dis_par, cond):
    '''Функция выдает максимальное число последовательно идущих от начала элементов списка par_list,
    сумма весов которых не превосходит max_sum.
    Отображение dis_par сопоставляет каждому элементу списка par_list его вес '''
    current_sum = 0
    position_shift = 0
    while (current_sum <= max_sum) and (position_shift != len(par_list)):
        par_value = par_list[position_shift]
        if not gl.USE_RELATIONS_OF_PARAMETORS or cond(par_value):
            current_sum += dis_par[par_value]
        position_shift += 1
    #if not (current_sum <= max_sum): # ошибка
    #    position_shift -= 1
    return position_shift

def corr_shift(par_list, position_shift, coord):
    '''Корректировка position_shift в случае, когда par_list[position_shift:] и par_list[:position_shift]
    содержат узлы, одинаковые по координате coord.'''
    if position_shift == 0 or position_shift == len(par_list):
        return position_shift
    val_left = par_list[position_shift - 1][coord]
    val_right = par_list[position_shift][coord]
    while val_left == val_right:
        position_shift -= 1 # сдвигаеся влево
        if position_shift == 0:
            return position_shift
        val_right = val_left
        val_left = par_list[position_shift - 1][coord]
    return position_shift

def find_position(value, array, coord):
    # Элементы array наборы чисел одинаковой длины
    # Элементы array должны быть упорядоченны по coord-ий координате
    len_array = len(array)
    if len_array == 0:
        raise BaseException('searching position of the value in empty array')
    if value < array[0][coord]:
        left = 'left_limit'
        right = 0
        return (left, right)
    for i in xrange(len_array - 1):
        a_i = array[i][coord]
        a_si = array[i+1][coord]
        if value == a_i:
            left = i
            right = i
            return (left, right)
        if value < a_si:
            left = i
            right = i + 1
            return (left, right)
    left = len_array - 1
    if value == array[len_array - 1][coord]:
        right = left
    else:
        right = 'right_limit'
    return (left, right)

def get_reg_parnames(parname_list):
    parnames = []
    for parname in par.reg_seq:
        if parname in parname_list:
            parnames.append(parname)
    return parnames

def get_icv_parnames(parname_list):
    parnames = []
    for parname in par.icv_seq:
        if parname in parname_list:
            parnames.append(parname)
    return parnames

def pv_list_from_dic(pv_dic, parnames):
    tmp_list = []
    for parname in parnames:
        if pv_dic.has_key(parname):
            tmp_list.append(pv_dic[parname])
        else:
            tmp_list.append(par.default_value[parname])
    return tuple(tmp_list)

def get_value(parname, value_par, inf_value_par, sup_value_par, position, min_position, max_position, coord):
    if (par.cond[parname] == par.gr) or (par.cond[parname] == par.less_eq):
        if position != min_position:
            return value_par[parname][position - 1][coord]
        else:
            return inf_value_par[parname]
    elif (par.cond[parname] == par.gr_eq) or (par.cond[parname] == par.less):
        if position != max_position:
            return value_par[parname][position][coord]
        else:
            return sup_value_par[parname]
        
def optimize(procs_dic, par_names,
             every_proc_is_individual_task = False,\
             par_start_value = None,\
             rand_par_start_value = False,\
             output = None,\
             dis_regpar = None,\
             dis_icvpar = None,
             run_result_default = None,
             val_F_start = None,
             result_start = None,
             new_stat_for_every_step = gl.GAIN_STAT_ON_EVERY_OPTIMIZATION_STEP
            ):
    '''
    procs_dic: taskname -> list_of_some_procnames_of_taskname (for some taskname)
    if procs_dic[taskname] is equal to None, then procs_dic[taskname] := all procnames of taskname
    '''
    
    # объеденим отображения index_in_reg_seq и index_in_icv_seq в index_in_own_seq
    index_in_own_seq = dict(stat.index_in_reg_seq)
    index_in_own_seq.update(stat.index_in_icv_seq)
    
    # выделяем из списка заданных параметров в отдельные упорядоченные списки параметры фазы regions и if_conv
    reg_parnames = get_reg_parnames(par_names)
    icv_parnames = get_icv_parnames(par_names)
    
    # установка значения по умолчанию для параметров
    par_default_value = {}
    for parname in reg_parnames + icv_parnames:
            par_default_value[parname] = par.default_value[parname]
    
    # установка начальных значений для параметров
    if par_start_value == None:
        if rand_par_start_value:
            raise BaseException('option rand_par_start_value is not work')
        else:
            par_start_value = par_default_value
    else:
        # в par_start_value могут быть заданы значения для тех параметров, которых нет в par_names,
        # и наоборот, не всем параметрам из par_names отображение par_start_value может сопоставлять значения.
        # Дополним par_start_value значениями по умолчанию для тех параметров из par_names,
        # которым par_start_value не сопоставлет никакого значения
        tmp_dict = dict(par_default_value)
        tmp_dict.update(par_start_value)
        par_start_value = tmp_dict
    
    # вычисление времени компиляции, времени исполнения и потребляемтой памяти заданных спеков при значении параметров по умолчанию
    # генерация статистики, если new_stat_for_every_step == True
    flag = every_proc_is_individual_task
    if run_result_default == None:
        result_default = calculate_abs_values(procs_dic, par_default_value, separate_procs = flag, output = output)
        j_for_exec_run = 1
    else:
        result_default = run_result_default
        j_for_exec_run = 0
    
    # вычисление значения функционала при значении параметров по умолчанию
    val_F_default = calculate_F(result_default, result_default)
    
    # вычисление значения функционала при начальном значении параметров
    if par_start_value == par_default_value:
        val_F_current = val_F_default
    else:
        if val_F_start == None:
            if result_start == None:
                result_start = calculate_abs_values(procs_dic, par_start_value, separate_procs = flag, output = output)
            j_for_exec_run += 1
            val_F_current = calculate_F(result_start, result_default)
        else:
            val_F_current = val_F_start
    par_current_value = dict(par_start_value)
    print >> output, 'F(...) = ', val_F_current
    print >> output
    
    # вычисление функции весов характеристик, отвечающим заданным параметрам фазы regions
    if len(reg_parnames) != 0:
        if dis_regpar == None:
            dis_regpar = stat.get_dis_regpar(procs_dic)
            stat.weight.normolize_dict(dis_regpar)
    
    # вычисление функции весов характеристик, отвечающим заданным параметрам фазы if_conv
    if len(icv_parnames) != 0:
        if dis_icvpar == None:
            dis_icvpar = stat.get_dis_icvpar(procs_dic)
            stat.weight.normolize_dict(dis_icvpar)
    
    # вычисление распределений параметров 
    value_par = stat.get_value_par(procs_dic, reg_parnames, icv_parnames, dis_regpar, dis_icvpar)
    
    # вычисление сглаженных распределений параметров (если соответстующая опция включена в smooth_stat)
    sm_dis = sm.get_sm_dis(value_par, reg_parnames, icv_parnames, dis_regpar, dis_icvpar)
             
    # установка начальных значений для лучшего значения функционала F, лучшего значения параметра
    # и шага алгоритма, на котором они достигаются
    i_for_best_value = 0
    if val_F_current < val_F_default:
        par_best_value = dict(par_current_value)
        result_best = dict(result_start)
        val_F_best = val_F_current
    else:
        par_best_value = dict(par_default_value)
        result_best = dict(result_default)
        val_F_best = val_F_default
    
    # инициализация базы данных для хранения всех найденных значений функционала F и распределений параметров
    F_run_result = ([], [], [], [])
    
    # добавление в базу соответсвующих значений при значении параметров по умолчанию
    F_run_result[0].append(par_default_value)
    F_run_result[1].append(val_F_default)
    F_run_result[2].append(None)
    F_run_result[3].append(None)
    
    # добавление в базу соответсвующих значений при начальном значении параметров
    F_run_result[0].append(dict(par_current_value))
    F_run_result[1].append(val_F_current)
    if DISTRIBUTION_DATABASE == True:
        F_run_result[2].append(deepcopy(value_par))
        F_run_result[3].append(deepcopy(sm_dis))
    else:
        F_run_result[2].append(None)
        F_run_result[3].append(None)
    
    j_for_temperature = 1 # задание начального уровня темпрературы
    iterr = 0 # инициализация счетчика внешних итераций алгоритма
    
    # current_to_new_candidate = False
    current_to_candidate = False # инициализация флага перехода алгоритма к новому набору параметров
    
    # основной цикл
    ind = 0
    while (iterr < MAX_NUMBER_ITERATIONS or (iterr < 3 * MAX_NUMBER_ITERATIONS and (iterr <= i_for_best_value + 1))):
        iterr += 1
        print >> output, 'Iteration ' + str(iterr) + ':'
        
        if new_stat_for_every_step and current_to_candidate:
            # ind = F_run_result[0].index(par_candidate_value) # ind уже вычисляли ранее
            if F_run_result[2][ind] == None: # если нет информации о распределении параметра в базе данных
                if len(reg_parnames) != 0:
                    dis_regpar = stat.get_dis_regpar(procs_dic)
                    stat.weight.normolize_dict(dis_regpar)
                if len(icv_parnames) != 0:
                    dis_icvpar = stat.get_dis_icvpar(procs_dic)
                    stat.weight.normolize_dict(dis_icvpar)
                value_par = stat.get_value_par(procs_dic, reg_parnames, icv_parnames, dis_regpar, dis_icvpar)
                sm_dis = sm.get_sm_dis(value_par, reg_parnames, icv_parnames, dis_regpar, dis_icvpar)
                if DISTRIBUTION_DATABASE == True:
                    F_run_result[2][ind] = deepcopy(value_par)
                    F_run_result[3][ind] = deepcopy(sm_dis)
            else:
                value_par = F_run_result[2][ind]
                sm_dis = F_run_result[3][ind]
            
        
        if (new_stat_for_every_step and current_to_candidate) or iterr == 1:
            sup_value_par = {}
            inf_value_par = {}
            for parname in reg_parnames + icv_parnames:
                i = index_in_own_seq[parname]
                sup_value_par[parname] = value_par[parname][-1][i] + 1 # число заведомо большее всех элементов value_par_list
                inf_value_par[parname] = max(value_par[parname][0][i] - 1, 0) # число заведомо меньшее всех элементов value_par_list или 0, если такого не бывает
            
            #поиск места текущих значений par_current_value в value_par
            min_position = {}
            max_position = {}
            position = {}
            for parname in reg_parnames + icv_parnames:
                min_position[parname] = 0
                max_position[parname] = len(value_par[parname])
                i = index_in_own_seq[parname]
                left, right = find_position(par_current_value[parname], value_par[parname], i)
                if right == 'right_limit':
                    right = max_position[parname]
                if (left == right) and ((par.cond[parname] == par.gr) or (par.cond[parname] == par.less_eq)):
                    position[parname] = right + 1
                else:
                    position[parname] = right
        
        current_reg_pv_list = pv_list_from_dic(par_current_value, par.reg_seq)
        current_icv_pv_list = pv_list_from_dic(par_current_value, par.icv_seq)
        
        max_step = temperature(j_for_temperature)
        print >> output, 'Temperature:', str(max_step * 100) + '%'
        for attempt in xrange(MAX_NUMBER_OF_ATTEMPTS_FOR_ITERATION + 1):
            # сдвигаемся в случайную точку, отстоящую не больше чем на max_step
            if attempt != MAX_NUMBER_OF_ATTEMPTS_FOR_ITERATION:
                #step_iterr_sum = abs(random.gauss(0, max_step))
                step_iterr_sum = abs(distribution(max_step))
            else:
                step_iterr_sum = max_step
            print >> output, 'Max sum of steps for all parametors:', str(step_iterr_sum * 100) + '%'
                
            step_iterr = {}
            for parnames in [reg_parnames, icv_parnames]:
                 # формируем случайные числа step_iterr[p_1], ..., step_iterr[p_n] такие,
                 # что step_iterr[p_1] + ... + step_iterr[p_n] = step_iterr_sum,
                 # где [p_1, ..., p_n] = parnames.
                if len(parnames) == 0:
                    continue
                sum_tmp = 0
                for parname in parnames:
                    tmp = random.uniform(0, 1)
                    step_iterr[parname] = tmp
                    sum_tmp += tmp
                koef_tmp = step_iterr_sum / sum_tmp
                for parname in parnames:
                    step_iterr[parname] *= koef_tmp
            print >> output, 'Steps for parametors:'
            print >> output, ' ', step_iterr
            
            print >> output, 'Directions for parametors:'
            attempt_is_bad = True
            new_reg_pv_list = []
            par_candidate_value = {}
            position_candidate = {}
            for parname in reg_parnames:
                coord = stat.index_in_reg_seq[parname]
                for i in xrange(len(new_reg_pv_list), coord):
                    tmp_parname = par.reg_seq[i]
                    if par_start_value.has_key(tmp_parname):
                        new_reg_pv_list.append(par_start_value[tmp_parname])
                    else:
                        new_reg_pv_list.append(par.default_value[tmp_parname])
                if parname in par.doub_kind: # если parname связан с дублированием узлов,
                    index_0_flag = True # то proc_opers_num может его блокировать
                else:
                    index_0_flag = False
                if parname in par.reg_extend_regn_list: # если parname связан с увеличением числа узлов в регионе,
                    index_1_flag = True # то regn_opers_num может его блокировать
                else:
                    index_1_flag = False
                cond = lambda x_list: condition(x_list, coord, current_reg_pv_list, new_reg_pv_list, index_0_flag, index_1_flag)
                coin = random.choice([True, False])
                if coin:
                    right_list = value_par[parname][position[parname]:]
                    position_shift = shift(right_list, step_iterr[parname], sm_dis[parname], cond)
                    position_shift = corr_shift(right_list, position_shift, coord)
                    print >> output, ' ', parname, ': ->'
                else:
                    left_list = value_par[parname][:position[parname]]
                    left_list.reverse()
                    position_shift = shift(left_list, step_iterr[parname], sm_dis[parname], cond)
                    position_shift = - corr_shift(left_list, position_shift, coord)
                    print >> output, ' ', parname, ': <-'
                if position_shift != 0:
                    attempt_is_bad = False
                    
                position_candidate[parname] = position[parname] + position_shift
                par_candidate_value[parname] = \
                    get_value(parname, value_par, inf_value_par, sup_value_par,\
                              position_candidate[parname], min_position[parname], max_position[parname], coord)
                
                new_reg_pv_list.append(par_candidate_value[parname])
            
            new_icv_pv_list = []
            for parname in icv_parnames:
                coord = stat.index_in_icv_seq[parname]
                for i in xrange(len(new_icv_pv_list), coord):
                    tmp_parname = par.icv_seq[i]
                    if par_start_value.has_key(tmp_parname):
                        new_icv_pv_list.append(par_start_value[tmp_parname])
                    else:
                        new_icv_pv_list.append(par.default_value[tmp_parname])
                cond = lambda x_list: icv_condition(x_list, coord, current_icv_pv_list, new_icv_pv_list)
                coin = random.choice([True, False])
                if coin:
                    right_list = value_par[parname][position[parname]:]
                    position_shift = shift(right_list, step_iterr[parname], sm_dis[parname], cond)
                    position_shift = corr_shift(right_list, position_shift, coord)
                    print >> output, ' ', parname, ': ->'
                else:
                    left_list = value_par[parname][:position[parname]]
                    left_list.reverse()
                    position_shift = shift(left_list, step_iterr[parname], sm_dis[parname], cond)
                    position_shift = - corr_shift(left_list, position_shift, coord)
                    print >> output, ' ', parname, ': <-'
                if position_shift != 0:
                    attempt_is_bad = False
                position_candidate[parname] = position[parname] + position_shift
                par_candidate_value[parname] = \
                    get_value(parname, value_par, inf_value_par, sup_value_par,\
                              position_candidate[parname], min_position[parname], max_position[parname], coord)
                new_icv_pv_list.append(par_candidate_value[parname])
                
            if attempt_is_bad:
                continue
            else:
                break
        else:
            print >> output, 'There is not variants for candidate values in step', iterr, 'of the algorithm'
            print >> output
            #if DECREASE_TEMPERATURE_BEFORE_UNFORTUNATE_ITERATIONS:
            #        j_for_temperature += 1
            continue
        
        tmp_dict = dict(par_start_value)
        tmp_dict.update(par_candidate_value)
        par_candidate_value = tmp_dict
        
        candidate_is_new = False
        if par_candidate_value in F_run_result[0]:
            print >> output, 'There is F(result of run.sh on par_dict = ' + str(par_candidate_value) + ') in our database'
            ind = F_run_result[0].index(par_candidate_value)
            val_F_candidate = F_run_result[1][ind]
        else:
            candidate_is_new = True
            result_candidate = calculate_abs_values(procs_dic, par_candidate_value, separate_procs = flag, output = output)
            j_for_exec_run += 1
            val_F_candidate = calculate_F(result_candidate, result_default)
            F_run_result[0].append(dict(par_candidate_value))
            F_run_result[1].append(val_F_candidate)
            F_run_result[2].append(None)
            F_run_result[3].append(None)
            ind = -1
        print >> output, 'F(...) = ', val_F_candidate
        
        if val_F_candidate < val_F_best:
            par_best_value = dict(par_candidate_value)
            if candidate_is_new:
                result_best = dict(result_candidate)
            else:
                raise BaseException('There is imposible. Not new list of pars is the best')
            val_F_best = val_F_candidate
            i_for_best_value = iterr
        
        current_to_candidate = False
        if val_F_candidate < val_F_current:
            current_to_candidate = True
            par_current_value = par_candidate_value
            val_F_current = val_F_candidate
            j_for_temperature += 1
            if not new_stat_for_every_step:
                    position = position_candidate
            print >> output, 'Moving to the better value'
        else:
            delta_val_F = val_F_candidate - val_F_current
            chance_move = math.exp(- delta_val_F / temperature(j_for_temperature))
            if chance_move > random.random():
                current_to_candidate = True
                par_current_value = par_candidate_value
                val_F_current = val_F_candidate
                j_for_temperature += 1
                if not new_stat_for_every_step:
                    position = position_candidate
                print >> output, 'Moving to the not better value with chance_move =', chance_move
            else:
                if DECREASE_TEMPERATURE_BEFORE_UNFORTUNATE_ITERATIONS:
                    j_for_temperature += 1
                print >> output, 'Not moving to the candidate value with chance_move =', chance_move
        
        # current_to_new_candidate = current_to_candidate and candidate_is_new
        print >> output
    
    print >> output, 'The best values for parametors are', par_best_value
    print >> output, 'The best values were found for', i_for_best_value, 'iterations of algorithm'
    print >> output, 'The run-scripts was started for', j_for_exec_run, 'times'
    print >> output, 'The best (t_c, t_e, m) is', result_best
    print >> output, 'The best value for F is', val_F_best
    
    return (par_best_value, val_F_best, result_best)

def seq_optimize(procs_dic, pargroup_seq,
             every_proc_is_individual_task = False,
             output = None,
             new_stat_for_every_step = gl.GAIN_STAT_ON_EVERY_OPTIMIZATION_STEP
            ):
    
    flag = every_proc_is_individual_task
    result_default = calculate_abs_values(procs_dic, {}, separate_procs = flag, output = output)
    par_current_value = None
    val_F_current = None
    result_current = None
    for par_group in pargroup_seq:
        print >> output, "---------------------------------------------------------------------------"
        print >> output, "Parameters:" + str(par_group)
        par_current_value, val_F_current, result_current = \
        optimize(procs_dic, par_group,
             every_proc_is_individual_task = flag,
             par_start_value = par_current_value,
             rand_par_start_value = False,
             output = output,
             dis_regpar = None,
             dis_icvpar = None,
             run_result_default = result_default,
             val_F_start = val_F_current,
             result_start = result_current,
             new_stat_for_every_step = new_stat_for_every_step
            )
    
    print >> output
    print >> output, 'The final best value for pars is', par_current_value
    print >> output, 'The final (t_c, t_e, m) is', result_current
    print >> output, 'The final value for F is', val_F_current
        
    return par_current_value, val_F_current, result_current

def dcs_optimize(procs_dic, dcs_zero_limit = gl.DSC_ZERO_LIMIT, result_default = None, output = None, nesting_off_attempt = False):
    
    j_for_exec_run = 0
    if result_default == None:
        #print >> output, 'dcs_level:', 0
        result_default = calculate_abs_values(procs_dic, {}, output = output)
        j_for_exec_run += 1
    val_F_default = calculate_F(result_default, result_default)
    print >> output, 'F(...) = ', val_F_default
        
    par_best_value = {}
    result_best = result_default
    val_F_best = val_F_default
        
    dis = stat.get_dcs_dis(procs_dic)
    for lv in gl.DCS_LEVELS:
        print >> output
        print >> output, 'dcs_level:', lv
        if dis[lv] > dcs_zero_limit:
            par_value = {'dcs_kill': True, 'dcs_level': lv}
            result_candidate = calculate_abs_values(procs_dic, par_value, output = output)
            j_for_exec_run += 1
            val_F_candidate = calculate_F(result_candidate, result_default)
            print >> output, 'F(...) = ', val_F_candidate
            if val_F_candidate < val_F_best:
                par_best_value = dict(par_value)
                result_best = dict(result_candidate)
                val_F_best = val_F_candidate
        else:
            print >> output, 'Dcs optimization in level', lv, 'will not be effective'
    
    if nesting_off_attempt == True:
        print >> output
        print >> output, 'Nesting off attempt'
        par_value = {'disable_regions_nesting' : False}
        result_candidate = calculate_abs_values(procs_dic, par_value, output = output)
        j_for_exec_run += 1
        val_F_candidate = calculate_F(result_candidate, result_default)
        print >> output, 'F(...) = ', val_F_candidate
        if val_F_candidate < val_F_best:
            par_best_value = dict(par_value)
            result_best = dict(result_candidate)
            val_F_best = val_F_candidate
    
    print >> output
    print >> output, 'The best values for parametors are', par_best_value
    print >> output, 'The run-scripts was started for', j_for_exec_run, 'times'
    print >> output, 'The best (t_c, t_e, m) is', result_best
    print >> output, 'The best value for F is', val_F_best
    
    return (par_best_value, val_F_best, result_best)
    
    
