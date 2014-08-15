from ctgbdg.database import engine, Base
from sqlalchemy import Column, Integer, String, Boolean, Table, Date, DateTime, Float,\
    Numeric
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from geoalchemy2 import Geometry
import fiona
from shapely.geometry import shape, Polygon, MultiPolygon
import json
import pyproj

def map_esri_type(esri_type):
    """ Map esri type (extracted through fiona) to SQLAlchemy type """
    tl = esri_type.split(':')
    t = tl[0]
    l = tl[1] if len(tl) > 1 else None
    if      t == 'int':        return Integer
    elif    t == 'double':     return Float(precision=15)
    elif    t == 'str':        return String(length=int(l) if l else 80)
    elif    t == 'date':       return Date
    elif    t == 'datetime':   return DateTime
    elif    t == 'float':
        if not l:              return Float
        else:
            ps = l.split('.')
            if len(ps) < 2:    return Float(precision=ps[0])
            else:              return Numeric(int(ps[0]), int(ps[1]))
            
def shp2table(name, metadata, schema, srid=4326, force_multipoly=False):
    """ Create a SQLAlchemy table schema from a shapefile schema opbtained through fiona
    """
    # Create a list of columns for the features' properties
    attr_list = []
    for p in schema['properties'].iteritems():
        attr_list.append(Column(p[0].lower(), map_esri_type(p[1])))
    # Create the geometry column
    geom_type = schema['geometry'].upper() if not force_multipoly \
        else 'MULTIPOLYGON'
    geom_col = Column('geom', Geometry(geom_type, srid=srid))
    attr_list.append(geom_col)
    table = Table(name, metadata, *attr_list, extend_existing=True)
    return table

def transform_proj(geom, source, target=4326):
    """Transform a geometry's projection.

    Keyword arguments:
    geom -- a (nested) list of points (i.e. geojson coordinates)
    source/target -- integer ESPG codes, or Proj4 strings
    """
    s_str = '+init=EPSG:{0}'.format(source) if type(source)==int else source
    t_str = '+init=EPSG:{0}'.format(target) if type(target)==int else target
    ps = pyproj.Proj(s_str, preserve_units=True)
    pt = pyproj.Proj(t_str, preserve_units=True)
    # This function works as a depth-first search, recursively calling itself until a
    # point is found, and converted (base case)
    if type(geom[0]) in (list, tuple):
        res = []
        for r in geom:
            res.append(transform_proj(r, source, target))
        return res
    else: # geom must be a point
        res = pyproj.transform(ps, pt, geom[0], geom[1])
        return list(res)

def import_shapefile(fpath, name, force_multipoly=False, proj_src=4326,
        proj_tgt=4326, proj4_src=None, proj4_tgt=None):
    """Import a shapefile into the PostGIS database.

    Keyword arguments:
    fpath -- path to a zipfile to be extracted
    name -- name given to the newly created table
    force_multipoly -- enforce that the gemoetries are multipolygons
    proj -- source projection spec (EPSG code - the PostGIS db must recognize)
    """
    # Open the shapefile with fiona.
    with fiona.open('/', vfs='zip://{0}'.format(fpath)) as shp:
        shp_table = shp2table(name, Base.metadata, shp.schema, srid=proj_tgt,
            force_multipoly=force_multipoly)
        shp_table.drop(bind=engine, checkfirst=True)
        shp_table.append_column(Column('row_id', Integer, primary_key=True))
        shp_table.create(bind=engine)
        features = []
        count = 0
        num_shapes = len(shp)
        for r in shp:
            # ESRI shapefile don't contemplate multipolygons, i.e. the geometry
            # type is polygon even if multipolygons are contained.
            # If and when the 1st multipoly is encountered, the table is
            # re-initialized.
            if not force_multipoly and r['geometry']['type'] == 'MultiPolygon':
                return import_shapefile(fpath, name, force_multipoly=True,
                        proj_src=proj_src, proj_tgt=proj_tgt,
                        proj4_src=proj_src, proj4_tgt=proj4_tgt)
            row_dict = dict((k.lower(), v) for k, v in r['properties'].iteritems())
            # GeoJSON intermediate representation
            try:
                geom_json = json.loads(str(r['geometry']).replace('\'', '"')\
                    .replace('(', '[').replace(')', ']'))
            except (ValueError, TypeError) as e:
                print 'Error at shape {0}'.format(count)
                print e
                print 'Geometry: {0}'.format(r['geometry'])
                count += 1
                continue
            # If the projection is not long/lat (WGS84 - EPGS:4326), transform.
            if proj_src != proj_tgt:
                geom_json['coordinates'] = transform_proj(geom_json['coordinates'],\
                    proj4_src if proj4_src else proj_src,\
                    proj4_tgt if proj4_tgt else proj_tgt)
            # Shapely intermediate representation, used to obtained the WKT
            geom = shape(geom_json)
            if force_multipoly and r['geometry']['type'] != 'MultiPolygon':
                geom = MultiPolygon([geom])
            row_dict['geom'] = 'SRID={0};{1}'.format(proj_tgt, geom.wkt)
            features.append(row_dict)
            count += 1
            #if count > 100: break
            # Buffer DB writes
            if not count % 1000 or count == num_shapes:
                try:
                    ins = shp_table.insert(features)
                    conn = engine.contextual_connect()
                    conn.execute(ins)
                except SQLAlchemyError as e:
                    print type(e)
                    return "Failed."
                features = []
                #print "Inserted {0} shapes in dataset {1}".format(count, name)
    return 'Table {0} created from shapefile'.format(name)
