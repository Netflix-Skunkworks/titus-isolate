from pprint import pformat
from six import iteritems


class OpportunisticResourceSpec():
    swagger_types = {
        'capacity': 'OpportunisticResourceCapacity',
        'window': 'OpportunisticResourceWindow',
    }

    attribute_map = {
        'capacity': 'capacity',
        'window': 'window',
    }

    def __init__(self, capacity=None, window=None):
        self._capacity = None
        self._window = None
        self.discriminator = None

        if capacity is not None:
            self.capacity = capacity
        if window is not None:
            self.window = window

    @property
    def capacity(self):
        """
        Gets the capacity of this OpportunisticResourceSpec.
        :return: The capacity of this OpportunisticResourceSpec.
        :rtype: OpportunisticResourceCapacity
        """
        return self._capacity

    @capacity.setter
    def capacity(self, capacity):
        """
        Sets the capacity of this OpportunisticResourceSpec.
        :param capacity: The capacity of this OpportunisticResourceSpec.
        :type: OpportunisticResourceCapacity
        """

        self._capacity = capacity

    @property
    def window(self):
        """
        Gets the window of this OpportunisticResourceSpec.
        :return: The window of this OpportunisticResourceSpec.
        :rtype: OpportunisticResourceWindow
        """
        return self._window

    @window.setter
    def window(self, window):
        """
        Sets the window of this OpportunisticResourceSpec.
        :param window: The window of this OpportunisticResourceSpec.
        :type: OpportunisticResourceWindow
        """

        self._window = window

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
        if not isinstance(other, OpportunisticResourceSpec):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        Returns true if both objects are not equal
        """
        return not self == other
