 树莓派谛听记录器:
 用于家里有女人,且经常说话不认帐时做对证用,其它用途可根据天猫精灵智能音箱的能力自行扩展. 配套调取录音文字及声音的原理是树莓派安装owncloud私有云盘,将录音文字,wav的目录配置成云数据共享,信息可以随时用手机打开.

 简介:
 语音采集器,靠近树莓派周围3-5米的人说话声音转成文字并记录下来,同时记录最近5句(可调)识别过有人说过话的原生wav录音.
 代码练习用.树莓派3B已稳定运行半年,因为效果好,树莓派一直没关机
 代码参考了 叮当——中文语音对话机器人里的代码,表示感谢
 https://github.com/dingdang-robot/dingdang-robot

 运行环境: 树莓派3B raspberrypi  
           树莓派zero使用1-2天会发生采集录音数据异常,内存耗尽,进程被kill问题,可能是因为zero内存只有512M
           3B上不关机连续运行了半年均正常

 配置:
 1.使用时需要修改 baidu_sound_rec.py 里面的这二个变量:
   api_key = "@@@@@@@@@@@@@@"
   api_secert = "@@@@@@@@@@@@@@"
    
 2.采集到的声音内容存在放 /myram/snowboy.log
 为减少文件经常读写损坏tf卡, 在/etc/rc.local时增加了如下语句将内存虚拟了10M成硬盘使用:
 sudo mount -t tmpfs -o size=10m,mode=0777 tmpfs /myram

 运行:
 python listener.py
