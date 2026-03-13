from googletrans import Translator
t = Translator()
res = t.translate('# ============= 核心框架 =============', dest='en')
print(res.text)
