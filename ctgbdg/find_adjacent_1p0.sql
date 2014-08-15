-- Flag adjacent buildings with 1.0 ft tolerance

-- Create the new 0.5 ft buffered geometry column
SELECT AddGeometryColumn('chicago_building_footprints',
    'geom_buf_0p5', 102671, 'MULTIPOLYGON', 2);

-- Populate it
UPDATE chicago_building_footprints
SET geom_buf_0p5 = ST_Multi(ST_Buffer(geom, 0.5, 'quad_segs=2'));

-- Create an index for it
CREATE INDEX idx_chicago_building_footprints_geom_bug_0p5
ON chicago_building_footprints USING GIST ( geom_buf_0p5 );

-- Add the adjacency flag
ALTER TABLE chicago_building_footprints
ADD adjacent_1p0 boolean DEFAULT 'false';

-- FInd adjacent buildings on the new buffered geometries
UPDATE chicago_building_footprints SET adjacent_1p0='true'i
WHERE row_id IN
    (SELECT t1.row_id FROM chicago_building_footprints t1 JOIN chicago_building_footprints t2
    ON t1.geom <> t2.geom AND ST_Intersects(t1.geom_buf_0p5, t2.geom_buf_0p5));
