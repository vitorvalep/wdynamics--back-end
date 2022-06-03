from math import *
from flask import Flask, request, json, jsonify
from pymongo import MongoClient
from datetime import datetime
from bson.json_util import dumps, loads

#informaçõe do banco de dados
client = MongoClient('localhost', 27017)
                        #database.collection
seesaw_collection = client.Simulations.SeeSaw


#Modelo de dados
'''{"dados_simulação":{
	"tempo": 10,
	"passo": 0.001
	},
"parametros_sistema":{
	"gravidade": 9.81,
	"massa_motor": 0.0025,
	"massa_contrapeso": 0,
	"massa_haste": 0.03,
	"compirmento_haste":0.535
	},
"hiper-parametros":{
	"lambda":5
	},
"setpoint":{
	"angulo":0,
	"velocidade_angular": 0,
	"aceleração_angular": 0
	},
"estados_iniciais":{
	"angulo":-0.78,
	"velocidade_angular": 0,
	"aceleração_angular": 0
	},
"simulação_incertezas":{
	"massa_motor": 1,
	"massa_contrapeso": 1,
	"compirmento_haste": 1
	}
}'''

api = Flask(__name__)

@api.route('/simulations/seesaw', methods=['POST','GET'])
def seesaw():
    if request.method == "POST":
        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            json_received = request.get_json()
            
            '''Variaveis de simulacao'''
            
            tempo = json_received['parametros_simulacao']['tempo'] #tempo de simulacao
            h = json_received['parametros_simulacao']['passo'] #passo de simulacao
            
            '''parametros do sistema'''
            g = json_received['parametros_sistema']['gravidade'] #m/s²
            m_m = json_received['parametros_sistema']['massa_motor'] #kg
            m_c = json_received['parametros_sistema']['massa_contrapeso']
            m_g = json_received['parametros_sistema']['massa_haste']
            l = json_received['parametros_sistema']['comprimento_haste']
            I_g = (m_g*l**2)/12

            '''Hiper-Parâmetros'''
            la = json_received['hiper-parametros']['lambda']

            '''Estados desejados'''
            th_d = json_received['setpoint']['angulo']
            z_d = json_received['setpoint']['velocidade_angular']
            th_pp_d = json_received['setpoint']['aceleracao_angular']

            '''Estados iniciais'''
            th = json_received['estados_iniciais']['angulo']
            z = json_received['estados_iniciais']['velocidade_angular']
            th_pp = json_received['estados_iniciais']['aceleracao_angular']
            f = 0

            '''Simulcao de incertezas'''
            e1 = json_received['simulacao_incertezas']['massa_motor']
            e2 = json_received['simulacao_incertezas']['massa_contrapeso']
            e3 = json_received['simulacao_incertezas']['comprimento_haste']
            
            '''inicialização de variaveis'''
            t = 0
            
            T = []
            TH = []
            TH_p = []
            TH_pp = []
            TH_d = []
            TH_p_d = []
            TH_pp_d = []
            E1 = []
            E2 = []
            E3 = []
            F = []
            Vo = []
        
            def f_th(th):
                r = 2*(e3*l)*(f + g*(e2*m_c - e1*m_m)*cos(th))/(4*I_g + (e3*l)**2*(e2*m_c) + (e3*l)**2*(e1*m_m))
                #r = "2*(e3*l)*(f + g*(e2*m_c - e1*m_m)*cos(th))/(4*I_g + (e3*l)**2*(e2*m_c) + (e3*l)**2*(e1*m_m))"
                return r
            #simulação
            while t < tempo:
                
                #Lei de controle
                v = th_pp_d - 2*la*(z - z_d) - (la**2)*(th - th_d)
                f = g*cos(th)*(m_m - m_c) + (2*I_g/l + l*m_c/2 + l*m_m/2)*v 

                #calculo de tensão fornecida ao motor
                if f>0: 
                    V = 23.3126202060078*sqrt(abs(f) + 0.0131289266304348) - 2.67119565217391
                else:
                    V = -(23.3126202060078*sqrt(abs(f) + 0.0131289266304348) - 2.67119565217391)
                
                th_k1 = z
                z_k1 = f_th(th)
                #=======================
                th_k2 = z + 0.5*h*z_k1
                z_k2 = f_th(th+0.5*h*th_k1)
                #=======================
                th_k3 = z + 0.5*h*z_k2
                z_k3 = f_th(th+0.5*h*th_k2)
                #=======================    
                th_k4 = z + h*z_k3
                z_k4 = f_th(th+h*th_k3)
                #=======================    
                #=======================
                th_f = th + (h/6)*(th_k1+2*th_k2+2*th_k3+th_k4) 
                z_f = z + (h/6)*(z_k1+2*z_k2+2*z_k3+z_k4)
                th_pp = f_th(th)
                
                T.append(t)
                TH.append(th)
                TH_p.append(z)
                TH_pp.append(th_pp)
                TH_d.append(th_d)
                TH_p_d.append(z_d)
                TH_pp_d.append(th_pp_d)
                E1.append(th-th_d)
                E2.append(z-z_d)
                E3.append(th_pp - th_pp_d)
                F.append(f)
                Vo.append(V)

                th = th_f
                z = z_f
                t = round(t + h, (int(f'{h:e}'.split('e')[-1])*-1))

            timestamp = round(datetime.timestamp(datetime.now()) * 1000)
            data = {"createdAt": timestamp,
                    "entrada_simulacao": json_received,
                    "saida_simulacao":{
                        "tempo": T,
                        "angulo":TH,
                        "velocidade_angular":TH_p,
                        "aceleracao_angular":TH_pp,
                        "angulo_desejado":TH_d,
                        "velocidade_angular_desejada":TH_p_d,
                        "aceleracao_angular_desejada":TH_pp_d,
                        "erro":E1,
                        "derivada_erro":E2,
                        "derivada2_erro":E3,
                        "forca_empuxo":F,
                        "tensao":Vo,
                }
            }

            seesaw_collection.insert_one(data)

            return "ok post"
        else:
            return 'Content-Type not supported!'
    
    if request.method == "GET":
        
        mydoc = seesaw_collection.find().sort("createdAt",1).limit(1)
        print(mydoc)
        mydoc = dumps(mydoc)        
        
        return mydoc

api.run(debug=True, host='0.0.0.0')