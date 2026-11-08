"""Build the slower, beginner version of the V6 guide from verified examples."""
import html
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('learning_renderer',HERE/'build_ai_v6_learning.py')
render=importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
render.ROOT=HERE.parent/'learning/ai_v6_de_hieu'
render.STEM='BAT_DAU_HOC_AI_V6'
render.ZIP_NAME='de_cuong_ai_v6_de_hieu'
render.BEGINNER=True


def body_html(items):
    sections=[];current=None
    for kind,body in items:
        if kind=='h1':continue
        if kind=='h2':
            current={'title':body,'parts':[]};sections.append(current)
        elif current is not None:
            if kind=='h3':value='<h3>'+render.inline(body)+'</h3>'
            elif kind=='p':
                if body.startswith('Lời giải:'):
                    value='<details class="answer"><summary>Xem lời giải</summary><p>'+render.inline(body)+'</p></details>'
                elif body.startswith('Tự hỏi:'):
                    value='<p class="question">'+render.inline(body)+'</p>'
                else:value='<p>'+render.inline(body)+'</p>'
            elif kind=='code':value='<pre><code>'+html.escape(body)+'</code></pre>'
            elif kind in ('ol','ul'):value='<'+kind+'>'+''.join('<li>'+render.inline(x)+'</li>' for x in body)+'</'+kind+'>'
            elif kind=='table':value='<div class="table-wrap"><table>'+''.join('<tr>'+''.join(('<th>' if i==0 else '<td>')+render.inline(x)+('</th>' if i==0 else '</td>') for x in row)+'</tr>' for i,row in enumerate(body))+'</table></div>'
            else:raise ValueError(kind)
            current['parts'].append(value)
    inserts=json.loads((render.ROOT/'tools/lesson_inserts.json').read_text())
    articles=[];links=[]
    for i,section in enumerate(sections):
        key='s'+str(i)
        links.append('<a href="#'+key+'">'+render.inline(section['title'])+'</a>')
        articles.append('<article id="'+key+'" class="lesson"'+(' hidden' if i else '')+'><h2>'+render.inline(section['title'])+'</h2>'+''.join(section['parts'])+inserts.get(str(i),'')+'</article>')
    return '\n'.join(articles),'\n'.join(links),[s['title'] for s in sections]


def main():
    root=render.ROOT
    items=render.blocks((root/(render.STEM+'.md')).read_text())
    render.pdf_document(items);render.word_document(items)
    articles,links,titles=body_html(items)
    template=(root/'tools/beginner_template.html').read_text()
    replacements={'<!--ARTICLES-->':articles,'<!--NAV-->':links,'__TITLES__':json.dumps(titles,ensure_ascii=False),
                  '__MODEL__':(root/'model/model.json').read_text(),'__FACTS__':(root/'VI_DU_DA_DOI_CHIEU.json').read_text()}
    for old,new in replacements.items():template=template.replace(old,new)
    (root/(render.STEM+'.html')).write_text(template)
    render.package()


if __name__=='__main__':main()
