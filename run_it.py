from ctgbdg.shapefiles import import_shapefile

if __name__=="__main__":
    import_shapefile('data/chicago_building_footprints.zip',
            'chicago_building_footprints', proj_src=102671,
            proj_tgt=102671)
