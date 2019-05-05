# -*- coding: utf-8-*-
import snowboydetect
import wave,time
from pyaudio import PyAudio, paInt16 
import numpy as np 
import sys,string
import baidu_sound_rec
from datetime import datetime
import logging
import tempfile
from threading import Thread
import threading
import gc
import urllib,os
import shutil

# 树莓派谛听记录器
# 用于家里有女人,且经常说话不认帐时做对证用,其它用途可根据天猫精灵智能音箱的能力自行扩展.
# 配套调取录音文字及声音的原理是树莓派安装owncloud私有云盘
# 将录音文字,wav的目录配置成云数据共享,这样用手机可以随时打开
#
# 简介:
# 语音采集器,靠近树莓派周围3-5米的人说话声音转成文字并记录下来
# 同时记录最近5句(可调)识别过有人说过话的原生wav录音.
# 代码练习用.树莓派3B已稳定运行半年,因为效果好,树莓派一直没关机
# 代码参考了 叮当——中文语音对话机器人里的代码,表示感谢
# https://github.com/dingdang-robot/dingdang-robot
#
# 运行环境: 树莓派3B raspberrypi  
#           树莓派zero使用1-2天会发生采集录音数据异常,内存耗尽,进程被kill问题,可能是因为zero内存只有512M
#           3B上不关机连续运行了半年均正常
#
# 使用前需要调整路径
# 采集到的声音内容存在放 /myram/snowboy.log
# 为减少文件经常读写损坏tf卡, 在/etc/rc.local时增加了如下语句将内存虚拟了10M成硬盘使用:
# sudo mount -t tmpfs -o size=10m,mode=0777 tmpfs /myram
#
# 配置:
# 使用时需要修改 baidu_sound_rec.py 里面的这二个变量:
#api_key = "@@@@@@@@@@@@@@"
#api_secert = "@@@@@@@@@@@@@@"
#
# 运行:
#python listener.py



#线程方式录音转文字的文字集合,最多同时5线程同时工作,目前只用到1线程,如要多线程,还需要调试
threadResult=[]
threadResult.append("")
threadResult.append("")
threadResult.append("")
threadResult.append("")
threadResult.append("")

#线程方式录音转文字的线程类
class Recorder_Thread(threading.Thread):
    def __init__(self, func, number,no):
        Thread.__init__(self)
        self.func = func
        self.args = number
        self.no=no
 
    def run(self):
        #time.sleep(2)
        threadResult[self.no] = self.func(self.args)
        #print threadResult[self.no]

        
model ="/home/pi/snowboy/snowboy.pmdl"

reload(sys)
sys.setdefaultencoding('utf8')   

logOutFilename='/myram/snowboy.log'  

# choose between DEBUG (log every information) or warning (change of state) or CRITICAL (only error)
#logLevel=logging.DEBUG
logLevel=logging.INFO
#logLevel=logging.CRITICAL


FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT,filename=logOutFilename,level=logLevel)

#刚启用录音时，前几秒丢掉
skiptime=2

LIST_MAXLEN=20  #20秒 最长录音10秒, 20秒够用了
list_sound=[None for i in range(LIST_MAXLEN)]
nowindex=0
#录音开始的时间指针
record_startindex=0
record_starttime=0
#1 开始识别
record_sound_status=0
 
detector = snowboydetect.SnowboyDetect(resource_filename="/home/pi/snowboy/resources/common.res",model_str=model)
checklist = []

def getwav(pa):
    wav_fp = wave.open('/myram/snowboy.wav', 'wb')
    wav_fp.setnchannels(1)
    wav_fp.setsampwidth(pa.get_sample_size(paInt16))
    wav_fp.setframerate(16000)
    #print "索引:",record_startindex, nowindex
    #nowindex这一列数据不要，因为数据是指向下一个，当前的数据还是空
    if (nowindex>record_startindex):   
        list1=    range(record_startindex,nowindex)
        for sound_p in list1:
            #print "get:", sound_p
            frames=list_sound[sound_p]
            if  frames is not None:
                wav_fp.writeframes(''.join(frames))   
        del list1                
    else:    
        list1= range(record_startindex,LIST_MAXLEN)
        for sound_p in list1:
            #print "get:", sound_p
            frames=list_sound[sound_p]
            if  frames is not None:
                wav_fp.writeframes(''.join(frames))   
        del list1                
        list1=range(0,nowindex)                
        for sound_p in list1:
            #print "get:", sound_p
            frames=list_sound[sound_p]
            if  frames is not None:
                wav_fp.writeframes(''.join(frames))   
        del list1                
    wav_fp.close()
    #f.seek(0)
    #return f

bakfile_index=1
#百度识别数据
def baidu_rec(pa):
    global record_sound_status
    global bakfile_index
    getwav(pa) 
    retstr=""
    try:
        retstr=baidu_sound_rec.baidu_rec_fn('/myram/snowboy.wav')
    except Exception as e:
        print "baidu_rec_fn异常:",e
    if len(retstr)>0:
        print "识别:",retstr
        #循环1,2,3...保存最近5次的录音原生wav文件
        if bakfile_index>6:
            bakfile_index=1                    
        shutil.copyfile("/myram/snowboy.wav","/myram/snowboy_"+str(bakfile_index)+".wav")
        retstr= " _" + str(bakfile_index)+".wav " + retstr
        bakfile_index=bakfile_index+1
        
        logging.info("识别:"+retstr + " " + datetime.now().strftime('%m-%d %H:%M'))        
        #把识别文件传给另一台总服务器记录(如果家里是别墅,每个房间需要安装一个监听器就有必要了上传了)
        #report_url = "http://192.168.1.20:1990/method=info&txt=20>"+ urllib.quote(retstr);
        #os.system("curl -X GET '"+ report_url+"'" )
    #声音识别完成,进入声音检测状态
    record_sound_status=0    
    print ">"    
    return retstr
    
def pop_sound(frames,flag):
    global nowindex,checklist
    if record_sound_status==1:
        if flag==0:
            checklist.append(0)
        else:
            checklist=[]
    if flag==9:
        print "pop_sound",nowindex,flag
    #if flag==1:
    #    print "pop_sound",nowindex,flag
    #print "pop_sound",nowindex,flag
    #print type(frames),len(frames)
    #print frames
    list_sound[nowindex]=frames
    #list_sound_flag[nowindex]=flag
    nowindex=nowindex+1
    if nowindex>=LIST_MAXLEN:        
        nowindex=0
        
        
def snowboy_check(frames):
    ans = detector.RunDetection(frames)
    if ans > 0:
        return 1
    else:
        return 0
        
 
#无限录音
def main():
    global record_sound_status,record_startindex,record_starttime,checklist,skiptime
    RATE = 16000
    CHUNK = 2000
    print sens
    detector.SetAudioGain(1)
    detector.SetSensitivity(str(sens))

    # number of seconds to allow to establish threshold
    THRESHOLD_TIME = 1
    pa = PyAudio()     
    # prepare recording stream
    stream = pa.open(format=paInt16,
                              channels=1,
                              rate=RATE,
                              input=True,
                              frames_per_buffer=CHUNK)
    stream.start_stream()
    skiptime=2
    print ">"                          
    try:                              
        #除非键盘中断，不用考虑退出
        loop1=1
        list1=range(0, RATE / CHUNK * THRESHOLD_TIME)
        while (True):
            #time.sleep(1)
            #1.录音1秒
            # stores the audio data
            frames = []
            starttime=time.time()
            # calculate the long run average, and thereby the proper threshold
            # 如果连接取数，则读取声音的时间和程序同步，如果等待，同因为缓存原因，读数据会很快           
          
            
            for i in list1:
                try:
                    #exception_on_overflow 这个参数很重要！
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    print "stream.read error",e
                    continue 
            if skiptime>0:
                skiptime=skiptime-1
                continue   

            #2.检查数据的音量,并放入20秒的音量缓冲区
            #如果发现有动静,转入监听状态
            #join 列表对象转成字符串
            val= snowboy_check(''.join(frames))
            #0 1.000633955
            #print val, time.time()-starttime
            
            #2.检查数据的音量,并放入20秒的音量缓冲区
            #如果发现有动静,转入监听状态
            if val>0:
                pop_sound(frames,1)
                if record_sound_status==0:
                    if nowindex>2:
                        record_startindex=nowindex-3;
                    elif  nowindex==2:
                        record_startindex=LIST_MAXLEN-1;
                    elif nowindex==1:
                        record_startindex=LIST_MAXLEN-2;
                    else:
                        record_startindex=LIST_MAXLEN-3;    
                    record_starttime=time.time()
                    print "record... ",datetime.now().strftime('%m-%d %H:%M')
                    #logging.info("record... "+ datetime.now().strftime('%m-%d %H:%M'))     
                    checklist=[]                    
                    record_sound_status=1 
            else:
                pop_sound(frames,0)
                
            #3.如果在监听状态,检查是否该停止监听
            if record_sound_status==1:
                #超过10秒,停止录音,并进行百度识别
                if time.time()-record_starttime>10 or  len(checklist)>2:
                    #百度识别 3-4秒就可以识别完成
                    print int(time.time()-record_starttime),"秒"
                    #logging.info(str(int(time.time()-record_starttime))+"秒")
                    task1 = Recorder_Thread(baidu_rec, pa,0)
                    task1.start()   
                    #进入声音文件识别状态
                    record_sound_status=3
                    #skiptime=5
            del frames
            loop1=loop1+1
            #20秒清一次
            if (loop1 % 20==0 and loop1!=0):
                gc.collect()        
                    
    except Exception as e:    
        #KeyboardInterrupt    
        print "中断退出:",e
        stream.stop_stream()
        stream.close()    

    return 0
    
#0.8基本上是有声音就会算唤醒了
sens=0.8
if len(sys.argv) > 1:
    sens= string.atof(sys.argv[1])    
    
main()
