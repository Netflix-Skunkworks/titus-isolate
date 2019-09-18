PERCENTILE_KEY = "precentile"
DURATION_KEY = "duration"


class DurationPrediction:

    def __init__(self, percentile: float, duration: float):
        self.__percentile = percentile
        self.__duration = duration

    def get_percentile(self) -> float:
        return self.__percentile

    def get_duration(self) -> float:
        return self.__duration

    def to_dict(self):
        return {
            PERCENTILE_KEY: self.get_percentile(),
            DURATION_KEY: self.get_duration()
        }


def deserialize_duration_prediction(body: dict) -> DurationPrediction:
    return DurationPrediction(
        float(body[PERCENTILE_KEY]),
        float(body[DURATION_KEY]))

