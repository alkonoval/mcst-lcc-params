﻿#!/usr/bin/python
# -*- coding: utf-8 -*-

# External imports
from __future__ import division # деление как в питон 3, т.е. вместо 3 / 2 = 1 будет 3 / 2 = 1.5
from sys import maxsize

# Internal imports
import global_vars as gl
import par, read, weight

def add_dic(dic, dic_plus):
    for key in dic_plus.iterkeys():
        if dic.has_key(key):
            dic[key] += dic_plus[key]
        else:
            dic[key] = dic_plus[key]
    

def get_dis_regpar(procs_dic):
    dis_par = {}
    for taskname, proc_list in procs_dic.iteritems():
        proc_cnt_dic = read.proc_cnt_dic(taskname)
        weight.normolize_dict(proc_cnt_dic)
        w_task = read.task_cnt(taskname)
        w_task = weight.task(w_task)
        if proc_list == None:
            proc_list = read.proc_list(taskname)
        for procname in proc_list:
            w_proc = proc_cnt_dic[procname]
            w_proc = weight.proc(w_proc)
            dis_par_proc = get_unnorm_dis_regpar_for_proc(taskname, procname)
            sum_tmp = sum(dis_par_proc.itervalues())
            if sum_tmp == 0:
                continue
            for key in dis_par_proc.iterkeys():
                dis_par_proc[key] = (dis_par_proc[key] / sum_tmp) * w_proc * w_task
            #dis_par = sum_dics(dis_par, dis_par_proc)
            add_dic(dis_par, dis_par_proc)
    return dis_par
            
def get_unnorm_dis_regpar_for_proc(taskname, procname):
            dis_par = {}
            proc = read.proc(taskname, procname)
            proc_max_cnt = float(proc.chars['max_cnt'])
            if not gl.DINUMIC_PROC_OPERS_NUM:
                proc_opers_num = int(proc.chars['opers_num']) # regn_max_proc_op_sem_size
            if proc_max_cnt == 0:
                return {}
            sum_reg_cnt = 0
            for regn in proc.regions.values():
                sum_reg_cnt += float(regn.chars['cnt'])
            for regn in proc.regions.values():
                reg_cnt = float(regn.chars['cnt'])
                if not gl.DINUMIC_REGN_OPERS_NUM:
                    reg_opers_num = int(regn.chars['opers_num']) # regn_opers_limit
                rel_reg_cnt = reg_cnt / sum_reg_cnt
                w_regn = weight.regn(reg_cnt, rel_reg_cnt)
                for node in regn.nodes.values():
                    if node.chars.has_key('n_cnt'):
                        if node.chars.has_key('s_enter'):
                            s_enter = int(node.chars['s_enter'])
                        else:
                            continue
                        n_cnt = float(node.chars['n_cnt'])
                        v_cnt = float(node.chars['v_cnt'])
                        w = weight.node(n_cnt, v_cnt, proc_max_cnt) * w_regn
                        key = []
                        if gl.DINUMIC_PROC_OPERS_NUM:
                            proc_opers_num = int(proc.chars['proc_opers_num']) # regn_max_proc_op_sem_size
                        key.append(proc_opers_num)
                        if gl.DINUMIC_REGN_OPERS_NUM:
                            reg_opers_num = int(regn.chars['regn_opers_num']) # regn_opers_limit
                        key.append(reg_opers_num)               
                        r_cnt = float(node.chars['r_cnt'])      # regn_heur1
                        key.append(r_cnt)
                        if s_enter:
                            key.append(r_cnt)                       # regn_heur2
                            o_cnt = float(node.chars['o_cnt'])      # regn_heur3
                            key.append(o_cnt)
                            p_cnt = float(node.chars['p_cnt'])      # regn_heur4
                            key.append(p_cnt)
                        else:
                            key.append(maxsize) # на узел без бокового входа параметры regn_heur2, regn_heur3, regn_heur4
                            key.append(maxsize) # не оказывают влияния
                            key.append(maxsize)
                        if node.chars.has_key('unb_max_dep') and node.chars.has_key('unb_sh_alt_prob'):
                            p = int(node.chars['unb_max_dep']) - int(node.chars['unb_min_dep']) # regn_disb_heur
                            key.append(p)
                            p = reg_cnt / proc_max_cnt                                          # regn_heur_bal1
                            key.append(p)
                            p = n_cnt / proc_max_cnt                                            # regn_heur_bal2
                            key.append(p) 
                            p = float(node.chars['unb_sh_alt_prob'])                            # regn_prob_heur
                            key.append(p)
                        else:
                            key.append(None)
                            key.append(None) # regn_heur_bal1, regn_heur_bal2 имеют смысл только,
                            key.append(None) # если мы определили несбалансированное схождение
                            key.append(None)
                                
                        key = tuple(key)
                        if dis_par.has_key(key):
                            dis_par[key] += w
                        else:
                            dis_par[key] = w
            return dis_par

def get_dis_icvpar(procs_dic):
    dis_par = {}
    for taskname, proc_list in procs_dic.iteritems():
        proc_cnt_dic = read.proc_cnt_dic(taskname)
        weight.normolize_dict(proc_cnt_dic)
        w_task = read.task_cnt(taskname)
        w_task = weight.task(w_task)
        if proc_list == None:
            proc_list = read.proc_list(taskname)
        for procname in proc_list:
            w_proc = proc_cnt_dic[procname]
            w_proc = weight.proc(w_proc)
            dis_par_proc = get_unnorm_dis_icvpar_for_proc(taskname, procname)
            sum_tmp = sum(dis_par_proc.itervalues())
            if sum_tmp == 0:
                continue
            for key in dis_par_proc.iterkeys():
                dis_par_proc[key] = (dis_par_proc[key] / sum_tmp) * w_proc * w_task
            add_dic(dis_par, dis_par_proc)
    return dis_par

def get_unnorm_dis_icvpar_for_proc(taskname, procname):
            dis_par = {}
            icv_proc = read.icv_proc(taskname, procname)
            sum_reg_cnt = 0
            for regn in icv_proc.regions.values():
                sum_reg_cnt += float(regn.chars['cnt'])
            if sum_reg_cnt == 0:
                return {}
            for _, regn in icv_proc.regions.iteritems():
                reg_cnt = float(regn.chars['cnt'])
                rel_reg_cnt = reg_cnt / sum_reg_cnt
                w_regn = weight.icv_regn(reg_cnt, rel_reg_cnt)
                for sect in regn.sects.values():
                    sect_cnt = float(sect.chars['cnt'])
                    w = weight.icv_sect(sect_cnt) * w_regn
                    key = []
                    o_num = int(sect.chars['o_num']) # ifconv_opers_num
                    c_num = int(sect.chars['c_num']) # ifconv_calls_num
                    key.append(o_num)
                    key.append(c_num)
                    if sect.chars.has_key('t_a'):
                        t_a = float(sect.chars['t_a'])
                        t_b = float(sect.chars['t_b'])
                        d_heur = float(sect.chars['d_heur']) # это адитивная добавка к ifconv_merge_heur?
                        if t_b != 0:
                            p = t_a / t_b - d_heur # ifconv_merge_heur
                        else:
                            if t_a == 0:
                                #p = 0
                                p = None # пользуемся тем, что None < pv для любого pv
                            else:
                                p = maxsize # считаем что maxsize > pv для любого возможного значения для pv
                        key.append(p)
                    else:
                        key.append(None)
                        # не знаю, что делать в этом случае. Этот случай бывает, когда sect не сливается из-за o_num и с_num и т.п.?
                    
                    key = tuple(key)
                    if dis_par.has_key(key):
                        dis_par[key] += w
                    else:
                        dis_par[key] = w
            return dis_par

index_in_reg_seq = par.index_in_reg_seq
index_in_icv_seq = par.index_in_icv_seq

def get_value_par(procs_dic, reg_parnames, icv_parnames, dis_regpar, dis_icvpar):
    # Также считывает при необходимости dis_regpar и dis_icvpar из статистики
    
    if len(reg_parnames) != 0:
        # получаем все узлы фазы regions процедур из procs_dic в неупорядоченном виде
        value_regpar = dis_regpar.keys()
    if len(icv_parnames) != 0:
        value_icvpar = dis_icvpar.keys()
       
    value_par = {}
    for parname in reg_parnames:
        value_one_regpar = list(value_regpar)
        i = index_in_reg_seq[parname]
        cmp_coord_i = lambda x, y: cmp(x[i], y[i])
        value_one_regpar.sort(cmp_coord_i)
        value_par[parname] = value_one_regpar
    for parname in icv_parnames:
        value_one_icvpar = list(value_icvpar)
        i = index_in_icv_seq[parname]
        cmp_coord_i = lambda x, y: cmp(x[i], y[i])
        value_one_icvpar.sort(cmp_coord_i)
        value_par[parname] = value_one_icvpar
    
    #надо просеять некоторые value_par[parname] от maxsize и None в своей координате (index_in_reg_seq[parname])
    for parname in ['regn_heur2', 'regn_heur3', 'regn_heur4']:
        if parname in reg_parnames:
            coord = index_in_reg_seq[parname]
            while value_par[parname][-1][coord] == maxsize: # maxsize > x, где 0 <= x <= 1.
                value_par[parname].pop()
    for parname in par.reg_unb:
        if parname in reg_parnames:
           coord = index_in_reg_seq[parname]
           # пользуемся тем, что None < x для любого x. Так как массив value_par[parname] упорядочен, то все None будут в начале.
           while value_par[parname][0][coord] == None:
               value_par[parname].pop(0)
    for parname in ['ifconv_merge_heur']:
        if parname in icv_parnames:
            coord = index_in_icv_seq[parname]
            while value_par[parname][0][coord] == None:
               value_par[parname].pop(0)
            while value_par[parname][-1][coord] == maxsize:
                value_par[parname].pop()
    
    return value_par

def get_dcs_proc_dis(dcs_proc,
                    koef_node_impotance = gl.DCS_KOEF_NODE_IMPOTANCE,
                    koef_edge_impotance = gl.DCS_KOEF_EDGE_IMPOTANCE,
                    koef_loop_impotance = gl.DCS_KOEF_LOOP_IMPOTANCE):
    
    pdis = [0] # распределение на нулевом уровне
    for lv in gl.DCS_LEVELS:
        nd = dcs_proc[lv].nd_num / dcs_proc[lv].n_num # процент мертвых узлов, выявленных на уровне lv оптимизации и не выявленных на предыдущих уровнях оптимизации
        ed = dcs_proc[lv].ed_num / dcs_proc[lv].e_num # процент мертвых ребер
        ld = dcs_proc[lv].ld_num / dcs_proc[lv].l_num # процент мертвых циклов
        impotance = koef_node_impotance * nd + koef_edge_impotance * ed + koef_loop_impotance * ld # значимость уровня lv оптимизации для данной процедуры
        #if impotance != 0:
        #    print '  ', dcs_proc[lv].procname, lv
        pdis.append(impotance)
    return pdis
    
def get_dcs_dis(procs_dic,
                koef_node_impotance = gl.DCS_KOEF_NODE_IMPOTANCE,
                koef_edge_impotance = gl.DCS_KOEF_EDGE_IMPOTANCE,
                koef_loop_impotance = gl.DCS_KOEF_LOOP_IMPOTANCE):
    dis = [0] * (gl.MAX_DCS_LEVEL + 1)
    sum_w_task = 0
    for taskname, proc_list in procs_dic.iteritems():
        if proc_list == None:
            proc_list = read.proc_list(taskname)
            
        time_proc_dic = read.proc_cnt_dic(taskname)
        sum_time = 0
        for procname in proc_list:
            sum_time += time_proc_dic[procname]
        
        w_task = read.task_cnt(taskname)
        w_task = weight.task(w_task)
        sum_w_task += w_task
        
        tdis = [0] * (gl.MAX_DCS_LEVEL + 1)
        for procname in proc_list:
            dcs_proc = read.dcs_proc(taskname, procname)
            pdis = get_dcs_proc_dis(dcs_proc,
                                    koef_node_impotance = koef_node_impotance,
                                    koef_edge_impotance = koef_edge_impotance,
                                    koef_loop_impotance = koef_loop_impotance)
            
            #print '   ', procname, pdis
            w_proc = weight.proc(time_proc_dic[procname])
            w_proc /= sum_time
            
            for lv in gl.DCS_LEVELS:
                tdis[lv] += w_proc * pdis[lv]
        
        for lv in gl.DCS_LEVELS:
            dis[lv] += w_task * tdis[lv]
            
    for lv in gl.DCS_LEVELS:
        dis[lv] /= sum_w_task
    
    return dis
