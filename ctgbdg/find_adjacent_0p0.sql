-- Flag adjacent buildings with 0 tolerance

-- Add the adjacency flag column
ALTER TABLE chicago_building_footprints
ADD adjacent_0p0 boolean DEFAULT 'false';

-- Find adjacent buildings
UPDATE chicago_building_footprints SET adjacent_0p0='true'
WHERE row_id IN (
    SELECT DISTINCT t1.row_id
    FROM chicago_building_footprints t1 JOIN chicago_building_footprints t2
    ON t1.geom <> t2.geom AND ST_Intersects(t1.geom, t2.geom)
);
