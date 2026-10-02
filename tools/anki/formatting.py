"""Shared plain-text and MathJax rendering. No arbitrary HTML interpretation."""
import re,html

def render_text(s):
    """Plain text + Anki MathJax. Never interpret arbitrary HTML/Markdown."""
    parts=re.split(r'(\\\[.*?\\\]|\\\(.*?\\\))',s,flags=re.S)
    result=[]
    for p in parts:
        if p.startswith(('\\[','\\(')):
            result.append(html.escape(p.replace('\n',' '),quote=False))
        else:result.append(html.escape(p,quote=False).replace('\n','<br>'))
    return ''.join(result)

def back_html(answer,extra='',source=''):
    b=render_text(answer)
    if extra:b+='<div class="anki-extra"><b>补充</b><br>'+render_text(extra)+'</div>'
    if source:b+='<div class="anki-source">出处：'+render_text(source)+'</div>'
    return b

