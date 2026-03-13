from googletrans import Translator
translator = Translator()
res = translator.translate('你好', dest='en')
print(res.text)
