class SIGTools(object):
    """
    This class collects all the sig functions  to use in TileVect, GeomConfig
    """

    @classmethod
    def get_extent_of_layer(cls, layer):
        """
        Outputs length of the smaller size of the features' bbox
        Returns 0 if the bbox is a Point
        """

        min_extent_features = float(0)

        # output might be a Point if single Point feature
        query = layer.get_extent()
        extent = query['extent']

        if extent:
            x1 = query['extent'][0]
            x2 = query['extent'][2]
            y1 = query['extent'][1]
            y2 = query['extent'][3]

            if x1 != x2 and y1 != y2:
                # not a point
                min_extent_features = min(float(abs(x2 - x1)), float(abs(y2 - y1)))

        return min_extent_features
