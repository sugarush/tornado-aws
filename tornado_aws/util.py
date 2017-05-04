
class XMLToDict(object):

    def __init__(self):
        self.tags = [ ]
        self.root = { }
        self.branch = self.root
        self.parent = self.root
        self.open = True

    def start(self, tag, attr):
        self.open = True
        self.tags.append(tag)
        #print 'Start: ', self.tags, tag

    def end(self, tag):
        self.open = False
        if self.tags[-1] == tag:
            self.tags.pop()
            self.branch = self.parent
        #print 'End: ', self.tags, tag

    def data(self, data):
        if not self.open:
            return

        tag = self.tags[-1]
        data = data.strip(' ').strip('\n')
        if data:
            self.branch[tag] = data
        else:
            self.parent = self.branch
            self.branch[tag] = { }
            self.branch = self.branch[tag]
        print 'Data: ', self.tags, tag

    def check(self, tag):
        if self.branch.get(tag):
            obj = { }
            for k, v in self.branch.items():
                obj[k] = v


    def close(self):
        return self.root


if __name__ == '__main__':

    from xml.etree.ElementTree import XMLParser

    branch = XMLToDict()
    parser = XMLParser(target=branch)
    print parser

    exampleXml = """
     <a>
       <b>test</b>
       <c>
         <d>
           <e>
           </e>
         </d>
       </c>
    </a>"""

    parser.feed(exampleXml)
    data = parser.close()
    print data
