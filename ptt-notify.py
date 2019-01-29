import configparser
import datetime
import re
import sys
import time

import requests
from PTTLibrary import PTT

# 讀取 config.ini
config = configparser.ConfigParser()
config.read('config.ini', encoding='UTF-8')

# 設定參數
Username = str(config['DEFAULT']['Username'])
Password = str(config['DEFAULT']['Password'])
LineAPI = str(config['DEFAULT']['LineAPI'])
RefreshInterval = int(config['DEFAULT']['RefreshInterval'])
LineContent = str(config['DEFAULT']['LineContent'])
BoardFilterDict = dict(config._sections['BOARD'])

# 宣告 PTTBot & 登入
PTTBot = PTT.Library()
LoginStatus = PTTBot.login(Username, Password)
if LoginStatus != PTT.ErrorCode.Success:
    PTTBot.Log('登入失敗')
    sys.exit()


#  時間戳
def timestamp():
    ts = '[' + datetime.datetime.now().strftime("%m-%d %H:%M:%S") + ']'
    return ts


# 利用 Line Notify 功能達成推送訊息
def sendMessage(message):
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': 'Bearer ' + LineAPI,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'message': message
    }
    r = requests.post(url, data=payload, headers=headers)
    if r.status_code == 200:
        print(timestamp() + '[資訊]' + ' Line 通知已傳送')
    else:
        print(timestamp() + '[警告]' + ' Line 通知傳送失敗 ' + str(r.content))


# 傳入看板名稱、關鍵字，回傳文章編號及內容
def getPTTNewestPost(boardname, filter):
    ErrCode, NewestIndex = PTTBot.getNewestIndex(Board=boardname)
    ErrCode, Post = PTTBot.getPost(boardname, PostIndex=NewestIndex)
    # 導入正規表達式判斷關鍵字
    regex = re.compile(filter, re.IGNORECASE)
    match = regex.search(str(Post.getTitle()))
    # 如果正規表達式有篩選到關鍵字（不為空），便向下執行
    if match is not None:
        print(timestamp() + '[資訊] ' + '符合篩選條件 - ' + boardname + ' ' + Post.getTitle())
        if LineContent == 'True':
            PostMessage = (
                boardname + '\n' + str(Post.getTitle()) + '\n' + str(Post.getWebUrl()) + '\n' + str(Post.getContent())
                )
        else:
            PostMessage = (
                boardname + '\n' + str(Post.getTitle()) + '\n' + str(Post.getWebUrl())
                )
        return NewestIndex, PostMessage
    # 如果沒篩選到關鍵字，則回傳文章編號 = 0 以及空訊息
    else:
        NewestIndex = 0
        PostMessage = ''
        return NewestIndex, PostMessage


# 建立當前看板及文章編號對應表
CurrentIndexDict = {}
for board, search in BoardFilterDict.items():
    CurrentIndexDict[board] = 0

NewestIndexDict = {}
# 每秒取得最新文章編號，若有更新才推送消息
try:
    while True:
        # 遍歷 BoardFilterDict，分別取得看板名稱 & 搜尋內容（support regex）
        for board, search in BoardFilterDict.items():
            NewestIndex, PostMessage = getPTTNewestPost(board, search)
            # 將各看板取得的最新文章編號放入 board: key value
            NewestIndexDict[board] = NewestIndex
            print(timestamp() + '[資訊] ' + board + ' 最新文章編號 ' + str(NewestIndex))
            # 比對當前 board: key value 以及最新的 board: key value 是否相同，若不同且不為 0 則推送消息
            if (CurrentIndexDict[board] != NewestIndexDict[board]) and (NewestIndexDict[board] != 0):
                sendMessage(PostMessage)
                CurrentIndexDict[board] = NewestIndex
        time.sleep(RefreshInterval)
except KeyboardInterrupt:
    print(timestamp() + '[資訊] 偵測到中斷指令')
    PTTBot.logout()
