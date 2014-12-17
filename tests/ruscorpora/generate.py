import os
import os.path
import xml.sax
import xml.sax.handler


class Extractor(xml.sax.handler.ContentHandler):
    def __init__(self, text_id):
        super().__init__()
        self.text_id = text_id
        self.paragraph_id = None
        self.tokens = None
        self.in_word = None

    def startElement(self, tag, attrs):
        if tag == 'w':
            self.in_word = True
        if tag == 'body':
            self.paragraph_id = 0
            self.tokens = []

    def characters(self, content):
        if self.paragraph_id is None:
            return

        if self.in_word:
            content = content.replace('`', '')
            tokens = [content]
        else:
            content = content.replace('\n', '').replace(' ', '')
            content = content.replace('--', '—')
            tokens = list(content)

        self.tokens.extend((t, False) for t in tokens)

    def endElement(self, tag):
        if tag == 'w':
            self.in_word = False
        if tag in ('se', 'p'):
            if self.tokens:
                token, _ = self.tokens[-1]
                self.tokens[-1] = token, True
        if tag in ('p', 'body'):
            path = os.path.join('tests', self.text_id, str(self.paragraph_id))
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, 'plaintext.txt'), 'w', encoding='utf-8') as plaintext_file, \
                 open(os.path.join(path, 'graphemes.txt'), 'w', encoding='utf-8') as graphemes_file:
                for token, is_end in self.tokens:
                    plaintext_file.write(token + ' ')
                    graphemes_file.write(('e' if is_end else 'n') + ' ' + token + '\n')
            self.paragraph_id += 1
            self.tokens = []

for base_dir, _, files in os.walk(os.path.normpath('ruscorpora_1M/texts')):
    for file in files:
        xml.sax.parse(os.path.join(base_dir, file), Extractor(os.path.splitext(file)[0]))
    break

