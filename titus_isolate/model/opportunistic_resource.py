from pprint import pformat
from six import iteritems

OPPORTUNISTIC_RESOURCE_GROUP = 'titus.netflix.com'
OPPORTUNISTIC_RESOURCE_VERSION = 'v1'
OPPORTUNISTIC_RESOURCE_API_VERSION = OPPORTUNISTIC_RESOURCE_GROUP + '/' + OPPORTUNISTIC_RESOURCE_VERSION
OPPORTUNISTIC_RESOURCE_KIND = 'OpportunisticResource'
OPPORTUNISTIC_RESOURCE_NAMESPACE = 'default'
OPPORTUNISTIC_RESOURCE_SINGULAR = 'opportunistic-resource'
OPPORTUNISTIC_RESOURCE_PLURAL = 'opportunistic-resources'
OPPORTUNISTIC_RESOURCE_NAME = OPPORTUNISTIC_RESOURCE_PLURAL + '.' + OPPORTUNISTIC_RESOURCE_GROUP
OPPORTUNISTIC_RESOURCE_FIELD_SELECTOR = 'metadata.name=' + OPPORTUNISTIC_RESOURCE_NAME

class OpportunisticResource():
    swagger_types = {
        'api_version': 'str',
        'kind': 'str',
        'metadata': 'V1ObjectMeta',
        'spec': 'OpportunisticResourceSpec'
    }

    attribute_map = {
        'api_version': 'apiVersion',
        'kind': 'kind',
        'metadata': 'metadata',
        'spec': 'spec'
    }

    def __init__(self, api_version=OPPORTUNISTIC_RESOURCE_API_VERSION, kind=OPPORTUNISTIC_RESOURCE_KIND, metadata=None,
                 spec=None):
        self._api_version = None
        self._kind = None
        self._metadata = None
        self._spec = None
        self.discriminator = None

        self.api_version = api_version
        self.kind = kind
        if metadata is not None:
            self.metadata = metadata
        self.spec = spec

    @property
    def api_version(self):
        """
        Gets the api_version of this OpportunisticResource.
        APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized
        schemas to the latest internal value, and may reject unrecognized values.
        More info: https://git.k8s.io/community/contributors/devel/api-conventions.md#resources
        :return: The api_version of this OpportunisticResource.
        :rtype: str
        """
        return self._api_version

    @api_version.setter
    def api_version(self, api_version):
        """
        Sets the api_version of this OpportunisticResource.
        APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized
        schemas to the latest internal value, and may reject unrecognized values.
        More info: https://git.k8s.io/community/contributors/devel/api-conventions.md#resources
        :param api_version: The api_version of this OpportunisticResource.
        :type: str
        """

        self._api_version = api_version

    @property
    def kind(self):
        """
        Gets the kind of this OpportunisticResource.
        Kind is a string value representing the REST resource this object represents. Servers may infer this from the
        endpoint the client submits requests to. Cannot be updated. In CamelCase.
        More info: https://git.k8s.io/community/contributors/devel/api-conventions.md#types-kinds
        :return: The kind of this OpportunisticResource.
        :rtype: str
        """
        return self._kind

    @kind.setter
    def kind(self, kind):
        """
        Sets the kind of this OpportunisticResource.
        Kind is a string value representing the REST resource this object represents. Servers may infer this from the
        endpoint the client submits requests to. Cannot be updated. In CamelCase.
        More info: https://git.k8s.io/community/contributors/devel/api-conventions.md#types-kinds
        :param kind: The kind of this OpportunisticResource.
        :type: str
        """

        self._kind = kind

    @property
    def metadata(self):
        """
        Gets the metadata of this OpportunisticResource.
        :return: The metadata of this OpportunisticResource.
        :rtype: V1ObjectMeta
        """
        return self._metadata

    @metadata.setter
    def metadata(self, metadata):
        """
        Sets the metadata of this OpportunisticResource.
        :param metadata: The metadata of this OpportunisticResource.
        :type: V1ObjectMeta
        """

        self._metadata = metadata

    @property
    def spec(self):
        """
        Gets the spec of this OpportunisticResource.
        Spec describes how the user wants the resources to appear
        :return: The spec of this OpportunisticResource.
        :rtype: OpportunisticResourceSpec
        """
        return self._spec

    @spec.setter
    def spec(self, spec):
        """
        Sets the spec of this OpportunisticResource.
        Spec describes how the user wants the resources to appear
        :param spec: The spec of this OpportunisticResource.
        :type: OpportunisticResourceSpec
        """
        if spec is None:
            raise ValueError("Invalid value for `spec`, must not be `None`")

        self._spec = spec

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
        if not isinstance(other, OpportunisticResource):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        Returns true if both objects are not equal
        """
        return not self == other
