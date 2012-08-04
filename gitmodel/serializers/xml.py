"""
XML serializer.
"""

from gitmodel.serializers import base
from xml.dom import pulldom
from xml.sax.saxutils import XMLGenerator

class SimplerXMLGenerator(XMLGenerator):
    def addQuickElement(self, name, contents=None, attrs=None):
        "Convenience method for adding an element with no children"
        if attrs is None: attrs = {}
        self.startElement(name, attrs)
        if contents is not None:
            self.characters(contents)
        self.endElement(name)

class Serializer(base.Serializer):
    """
    Serializes a QuerySet to XML.
    """

    def indent(self, level):
        if self.options.get('indent', None) is not None:
            self.xml.ignorableWhitespace('\n' + ' ' * self.options.get('indent', None) * level)

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        self.xml = SimplerXMLGenerator(self.stream, self.options.get("encoding", "utf-8"))
        self.xml.startDocument()
        self.xml.startElement("gitmodel-object", {"version" : "1.0"})

    def end_serialization(self):
        """
        End serialization -- end the document.
        """
        self.indent(0)
        self.xml.endElement("gitmodel-object")
        self.xml.endDocument()


    def handle_field(self, obj, field):
        """
        Called to handle each field on an object (except for ForeignKeys and
        ManyToManyFields)
        """
        self.indent(1)
        self.xml.startElement("field", {
            "name" : field.name,
            "type" : field.get_internal_type()
        })

        # Get a "string version" of the object's data.
        if getattr(obj, field.name) is not None:
            self.xml.characters(field.value_to_string(obj))
        else:
            self.xml.addQuickElement("None")

        self.xml.endElement("field")


class Deserializer(base.Deserializer):
    """
    Deserialize XML.
    """
    def deserialize(self, data):
        self.event_stream = pulldom.parse(data)
        for event, node in self.event_stream:
            if event == "START_ELEMENT" and node.nodeName == "field":
                self.event_stream.expandNode(node)
                return self._handle_field(node)

    def _handle_field(self, node):
        """
        Convert an <field> node to a DeserializedObject.
        """
        # Deseralize each field.
        # If the field is missing the name attribute, bail (are you
        # sensing a pattern here?)
        
        attrs = {}

        field_name = node.getAttribute("name")
        if not field_name:
            raise base.DeserializationError("<field> node is missing the 'name' attribute")

        # Get the field from the Model. This will raise a
        # FieldDoesNotExist if, well, the field doesn't exist, which will
        # be propagated correctly.
        field = self.model_class._meta.get_field(field_name)

        # As is usually the case, relation fields get the special treatment.
        if node.getElementsByTagName('None'):
            value = None
        else:
            value = field.to_python(getInnerText(node).strip())
        attrs[field.name] = value

        return self.model_class(**attrs)


def getInnerText(node):
    """
    Get all the inner text of a DOM node (recursively).
    """
    # inspired by http://mail.python.org/pipermail/xml-sig/2005-March/011022.html
    inner_text = []
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE or child.nodeType == child.CDATA_SECTION_NODE:
            inner_text.append(child.data)
        elif child.nodeType == child.ELEMENT_NODE:
            inner_text.extend(getInnerText(child))
        else:
           pass
    return u"".join(inner_text)
