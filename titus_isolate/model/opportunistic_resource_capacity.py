from pprint import pformat
from six import iteritems


class OpportunisticResourceCapacity():
    swagger_types = {
        'cpu': 'float',
    }

    attribute_map = {
        'cpu': 'cpu',
    }

    def __init__(self, cpu=None):
        self._cpu = None
        self.discriminator = None

        if cpu is not None:
            self.cpu = cpu

    @property
    def cpu(self):
        """
        Gets the cpu of this OpportunisticResourceCapacity.
        :return: The cpu of this OpportunisticResourceCapacity.
        :rtype: OpportunisticResourceCpu
        """
        return self._cpu

    @cpu.setter
    def cpu(self, cpu):
        """
        Sets the cpu of this OpportunisticResourceCapacity.
        :param cpu: The cpu of this OpportunisticResourceCapacity.
        :type: OpportunisticResourceCpu
        """

        self._cpu = cpu

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
        if not isinstance(other, OpportunisticResourceCapacity):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        Returns true if both objects are not equal
        """
        return not self == other
