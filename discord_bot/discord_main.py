# import discord, requests, json, os
# from keep_alive import keep_alive

# ORDER_BOT_TOKEN = os.environ['ORDER_BOT_TOKEN']
# WEBHOOK_URL = os.environ['WEBHOOK_URL']
# WEBHOOK_PASSPHRASE = os.environ['WEBHOOK_PASSPHRASE']

# client = discord.Client()

# def post_tradingview-webhook(payload):
#   r = requests.post(WEBHOOK_URL, data=payload)
#   json_res = r.json()
#   print(json_res)
#   return(json_res['success'])


# @client.event
# async def on_ready():
#   print('Successfully logged in as {0.user}'.format(client))


# @client.event
# async def on_message(message):
#   if message.author == client.user:
#     return

#   msg = message.content
  
#   if msg.startswith('!ping'):
#     await message.channel.send(f"Pong! ({client.latency*1000}ms)")

#   if msg.startswith('!mirror '):
#     await message.channel.send(msg[len('!mirror '):])

#   if msg.startswith('!payload '):
#     data = json.loads(msg[len('!payload '):])
#     data['passphrase'] = WEBHOOK_PASSPHRASE
#     await message.channel.send('Payload received, now processing...')
#     success = post_tradingview-webhook(json.dumps(data))

#     if success:
#       await message.channel.send(':white_check_mark: Order posted with success !')
#     else:
#       await message.channel.send(':x: An error must have occured, please check the logs for more information...')   


# keep_alive()
# client.run(ORDER_BOT_TOKEN)
