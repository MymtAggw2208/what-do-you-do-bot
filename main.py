import os
import base64, hashlib, hmac
import urllib.parse

from flask import abort, jsonify

from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    TemplateSendMessage,ButtonsTemplate,MessageAction,URIAction
)

conversation_status = {}
questions = ['ご予定は？','何食べたい？','何したい？','どこ行きたい？']
selections = [{1:'ごはん',2:'あそび',3:'メンテ'},
              ['和食','洋食','中華'],
              ['運動','ゲーム','読書','映画'],
              ['マッサージ','美容院','病院']]

def main(request):
    channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

    line_bot_api = LineBotApi(channel_access_token)
    parser = WebhookParser(channel_secret)

    body = request.get_data(as_text=True)
    hash = hmac.new(channel_secret.encode('utf-8'),
        body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode()

    if signature != request.headers['X_LINE_SIGNATURE']:
        return abort(405)

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return abort(405)

    for event in events:
        if isinstance(event, MessageEvent):
            if isinstance(event.message, TextMessage):
                reply_data = []
                # IDを取得する
                userid = event.source.user_id
                if userid not in conversation_status:
                    # 会話履歴がない場合、会話開始
                    conversation_status[userid] = 0
                    reply_data.append(make_button_template(0))
                else:
                    # 会話履歴が残っている場合、返答内容をチェック
                    if conversation_status[userid] == 0:
                        # 0の場合、選択肢から返信しているかどうかチェック
                        if event.message.text in selections[0].values():
                            # 存在する場合はkeyを次の質問の添え字として使用
                            for key, value in selections[0].items():
                                if value == event.message.text:
                                    conversation_status[userid] = key
                                    reply_data.append(make_button_template(key))
                        else:
                            # 存在しない場合、質問を再送信
                            reply_data.append(TextSendMessage(text='ボタンから選んでね'))
                            reply_data.append(make_button_template(0))
                    else:
                        # 0以外の場合、選択肢から返信しているかどうかチェック
                        if event.message.text in selections[conversation_status[userid]]:
                            # 存在する場合、キーワード指定してGoogleMapへ
                            reply_data.append(
                                TemplateSendMessage(
                                    alt_text='探したよ！',
                                    template=ButtonsTemplate(
                                        text = '探したよ！',
                                        actions=[
                                            URIAction(
                                                label='GoogleMap',   
                                                uri='https://www.google.co.jp/maps/search/' + urllib.parse.quote(event.message.text) + '?openExternalBrowser=1'
                                            )
                                        ]
                                    )))
                            # ステータスを削除
                            del conversation_status[userid]
                        else:
                            # 存在しない場合、質問を再送信
                            reply_data.append(TextSendMessage(text='ボタンから選んでね'))
                            reply_data.append(make_button_template(conversation_status[userid]))
                    
                line_bot_api.reply_message(
                    event.reply_token,
                    reply_data
                )
            else:
                continue

    return jsonify({ 'message': 'ok'})

def make_button_template(idx):
    # ボタンをリスト化する
    button_list = []
    # selectionsから取得した内容がdictの場合
    if isinstance(selections[idx],dict):
        # 全ての値を取得してメッセージアクションを作成
        for key in selections[idx].values():
            button_list.append(
                MessageAction(
                    label=key,
                    text=key
                )
            )
    # selectionsから取得した内容がlistの場合
    else:
        # 全要素を取得してメッセージアクションを作成
        for item in selections[idx]:
            button_list.append(
                MessageAction(
                    label=item,
                    text=item
                )
            )
    message_template = TemplateSendMessage(
        alt_text=questions[idx],
        template=ButtonsTemplate(
            text = questions[idx],            
            actions=button_list
        )
    )
    return message_template
