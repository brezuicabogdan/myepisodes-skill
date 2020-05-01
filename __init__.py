from mycroft import MycroftSkill, intent_file_handler


class Myepisodes(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('myepisodes.intent')
    def handle_myepisodes(self, message):
        self.speak_dialog('myepisodes')


def create_skill():
    return Myepisodes()

