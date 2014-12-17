import os
import os.path
import xml.sax
import xml.sax.handler


class Extractor(xml.sax.handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.text = None
        self.paragraph = None
        self.graphemes_file = None
        self.plaintext_file = None
        self.in_source = False
        self.previous_token = None

    def startElement(self, tag, attrs):
        if tag == 'token':
            if self.previous_token is not None:
                self.graphemes_file.write('n ')
                self.graphemes_file.write(self.previous_token)
                self.graphemes_file.write('\n')
            self.previous_token = attrs['text']
        elif tag == 'source':
            self.in_source = True
        elif tag == 'paragraph':
            self.paragraph = attrs['id']
            path = os.path.join('tests', self.text, self.paragraph)
            os.makedirs(path, exist_ok=True)
            self.plaintext_file = open(os.path.join(path, 'plaintext.txt'), 'w', encoding='utf-8')
            self.graphemes_file = open(os.path.join(path, 'graphemes.txt'), 'w', encoding='utf-8')
        elif tag == 'text':
            self.text = attrs['id']

    def characters(self, content):
        if self.in_source:
            self.plaintext_file.write(content)

    def endElement(self, tag):
        if tag == 'source':
            self.in_source = False
        elif tag == 'sentence':
            self.plaintext_file.write(' ')
            if self.previous_token is not None:
                self.graphemes_file.write('e ')
                self.graphemes_file.write(self.previous_token)
                self.graphemes_file.write('\n')
            self.previous_token = None
        elif tag == 'paragraph':
            self.graphemes_file.close()
            self.plaintext_file.close()
            self.graphemes_file = None
            self.plaintext_file = None
            self.paragraph = None
        elif tag == 'text':
            self.text = None

xml.sax.parse('annot.opcorpora.xml', Extractor())

