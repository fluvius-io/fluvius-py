from fluvius.domain.message import Message


class MQTTMessage(Message):
    class Meta(Message.Meta):
        pass

    def _dispatch(self, message: Message):
        pass