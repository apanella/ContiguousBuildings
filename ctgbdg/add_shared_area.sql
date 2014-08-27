-- Add estimated shared perimetral length a building shares with others
-- Add estimated area that a building shares with others

-- Compute the estimated area given the two heights and shared length
-- Parameters: heigth_1, heigth_2, shared_length
CREATE OR REPLACE FUNCTION est_shared_area(FLOAT, FLOAT, FLOAT) RETURNS FLOAT AS $$
DECLARE
    min_height FLOAT := 0.0;
    result FLOAT := 0.0;
BEGIN
    min_height = CASE
        WHEN ($1 < $2) THEN $1
        ELSE $2
    END;
    result = min_height * $3;
    -- Don't consider very small areas - usually bridges/walkways
    IF (result >= 200) THEN RETURN result;
    ELSE RETURN 0.0;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Add shared length column
-- ALTER TABLE chicago_building_footprints
-- ADD COLUMN adj_length float DEFAULT 0.0;
-- Add shared area column
ALTER TABLE chicago_building_footprints
ADD COLUMN adj_area FLOAT DEFAULT 0.0;

-- Estimate the shared area between buildings and add it to the table
UPDATE chicago_building_footprints t1
SET adj_area = (SELECT 
    sum(est_shared_area(t1.height, t2.height,
            ST_Perimeter(ST_Intersection(t1.geom_buf_0p5, t2.geom_buf_0p5)) / 2.0))
    FROM chicago_building_footprints AS t2
    WHERE t1.geom && t2.geom AND t1.bldg_id <> t2.bldg_id AND t1.adjacent_0p0)
--FROM chicago_building_footprints AS t1
;
