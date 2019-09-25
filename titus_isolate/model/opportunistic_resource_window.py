from pprint import pformat
from six import iteritems


class OpportunisticResourceWindow():
    swagger_types = {
        'start': 'int',
        'end': 'int',
    }

    attribute_map = {
        'start': 'start',
        'end': 'end',
    }

    def __init__(self, start=None, end=None):
        self._start = None
        self._end = None
        self.discriminator = None

        if start is not None:
            self.start = start
        if end is not None:
            self.end = end

    @property
    def start(self):
        """
        Gets the start of this OpportunisticResourceWindow.
        :return: The start of this OpportunisticResourceWindow.
        :rtype: OpportunisticResourceStart
        """
        return self._start

    @start.setter
    def start(self, start):
        """
        Sets the start of this OpportunisticResourceWindow.
        :param start: The start of this OpportunisticResourceWindow.
        :type: OpportunisticResourceStart
        """

        self._start = start

    @property
    def end(self):
        """
        Gets the end of this OpportunisticResourceWindow.
        :return: The end of this OpportunisticResourceWindow.
        :rtype: OpportunisticResourceEnd
        """
        return self._end

    @end.setter
    def end(self, end):
        """
        Sets the end of this OpportunisticResourceWindow.
        :param end: The end of this OpportunisticResourceWindow.
        :type: OpportunisticResourceEnd
        """

        self._end = end

    def to_dict(self):
        """
        Returns the model properties as a dict
        """
        result = {}

        for attr, _ in iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value

        return result

    def to_str(self):
        """
        Returns the string representation of the model
        """
        return pformat(self.to_dict())

    def __repr__(self):
        """
        For `print` and `pprint`
        """
        return self.to_str()

    def __eq__(self, other):
        """
        Returns true if both objects are equal
        """
        if not isinstance(other, OpportunisticResourceWindow):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        Returns true if both objects are not equal
        """
        return not self == other
