#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
webapp.py
=========
Implements IIIF 1.1 <http://www-sul.stanford.edu/iiif/image-api/1.1> level 2

    Copyright (C) 2013 Jon Stroop

    This program is free software: you can redistribute it and/or modify it 
    under the terms of the GNU General Public License as published by the Free 
    Software Foundation, either version 3 of the License, or (at your option) 
    any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT 
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for 
    more details.

    You should have received a copy of the GNU General Public License along 
    with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# from ConfigParser import RawConfigParser
from configobj import ConfigObj
from datetime import datetime
from decimal import Decimal, getcontext
from img_info import ImageInfo
from img_info import ImageInfoException
from img_info import InfoCache
from logging.handlers import RotatingFileHandler
from os import path, makedirs, unlink, removedirs, symlink
from parameters import RegionRequestException
from parameters import RegionSyntaxException
from parameters import RotationSyntaxException
from parameters import SizeRequestException
from parameters import SizeSyntaxException

from urllib import unquote, quote_plus
from werkzeug.http import parse_date, parse_accept_header, http_date
from werkzeug.wrappers import Request, Response, BaseResponse, CommonResponseDescriptorsMixin
import constants
import img
import logging
import loris_exception
import random
import re
import resolver
import string
import transforms

try:
    import libuuid as uuid # faster. do pip install python-libuuid
except ImportError:
    import uuid

# Loris's etc dir MUST either be a sibling to the loris/loris directory or at 
# the below:
ETC_DP = '/etc/loris'
# We can figure out everything else from there.

getcontext().prec = 25 # Decimal precision. This should be plenty.

def create_app(debug=False, debug_jp2_transformer='kdu'):
    global logger
    if debug:
        project_dp = path.dirname(path.dirname(path.realpath(__file__)))

        # read the config
        config_fp = path.join(project_dp, 'etc', constants.CONFIG_FILE_NAME)
        config = ConfigObj(config_fp, unrepr=True, interpolation=False)

        config['logging']['log_to'] = 'console'
        config['logging']['log_level'] = 'DEBUG'

        __configure_logging(config['logging'])

        logger = logging.getLogger('webapp')

        logger.debug('Running in debug mode.')

        # override some stuff to look at relative or tmp directories.
        config['loris.Loris']['www_dp'] = path.join(project_dp, 'www')
        config['loris.Loris']['tmp_dp'] = '/tmp/loris/tmp'
        config['loris.Loris']['enable_caching'] = True
        config['img.ImageCache']['cache_links'] = '/tmp/loris/cache/links'
        config['img.ImageCache']['cache_dp'] = '/tmp/loris/cache/img'
        config['img_info.InfoCache']['cache_dp'] = '/tmp/loris/cache/info'
        config['resolver']['impl'] = 'SimpleFSResolver' 
        config['resolver']['src_img_root'] = path.join(project_dp,'tests','img')
        
        if debug_jp2_transformer == 'opj':
            from transforms import OPJ_JP2Transformer
            opj_decompress = OPJ_JP2Transformer.local_opj_decompress_path()
            config['transforms']['jp2']['opj_decompress'] = path.join(project_dp, opj_decompress)
            libopenjp2_dir = OPJ_JP2Transformer.local_libopenjp2_dir()
            config['transforms']['jp2']['opj_libs'] = path.join(project_dp, libopenjp2_dir)
        else: # kdu
            from transforms import KakaduJP2Transformer
            kdu_expand = KakaduJP2Transformer.local_kdu_expand_path()
            config['transforms']['jp2']['kdu_expand'] = path.join(project_dp, kdu_expand)
            libkdu_dir = KakaduJP2Transformer.local_libkdu_dir()
            config['transforms']['jp2']['kdu_libs'] = path.join(project_dp, libkdu_dir)

    else:
        config_fp = path.join(ETC_DP, constants.CONFIG_FILE_NAME)
        config = ConfigObj(config_fp, unrepr=True, interpolation=False)
        __configure_logging(config['logging'])
        logger = logging.getLogger(__name__)
        logger.debug('Running in production mode.')


    # Make any dirs we may need 
    dirs_to_make = []
    try:
        dirs_to_make.append(config['loris.Loris']['tmp_dp'])
        if config['logging']['log_to'] == 'file':
            dirs_to_make.append(config['logging']['log_dir'])
        if config['loris.Loris']['enable_caching']:
            dirs_to_make.append(config['img.ImageCache']['cache_dp'])
            dirs_to_make.append(config['img.ImageCache']['cache_links'])
            dirs_to_make.append(config['img_info.InfoCache']['cache_dp'])
        [makedirs(d) for d in dirs_to_make if not path.exists(d)]
    except OSError as ose: 
        from sys import exit
        from os import strerror
        # presumably it's permissions
        msg = '%s (%s)' % (strerror(ose.errno),ose.filename)
        logger.fatal(msg)
        logger.fatal('Exiting')
        exit(77)
    else:
        return Loris(config, debug)

def __configure_logging(config):
    logger = logging.getLogger()

    conf_level = config['log_level']

    if conf_level == 'CRITICAL': LOG_LEVEL = logger.setLevel(logging.CRITICAL)
    elif conf_level == 'ERROR': LOG_LEVEL = logger.setLevel(logging.ERROR)
    elif conf_level == 'WARNING': LOG_LEVEL = logger.setLevel(logging.WARNING)
    elif conf_level == 'INFO': LOG_LEVEL = logger.setLevel(logging.INFO)
    else: LOG_LEVEL = logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt=config['format'])

    if config['log_to'] == 'file':
        if not getattr(logger, 'handler_set', None):
            fp = '%s.log' % (path.join(config['log_dir'], 'loris'),)
            handler = RotatingFileHandler(fp,
                maxBytes=config['max_size'], 
                backupCount=config['max_backups'],
                delay=True)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    else:
        # STDERR
        if not getattr(logger, 'handler_set', None):
            from sys import __stderr__, __stdout__
            err_handler = logging.StreamHandler(__stderr__)
            err_handler.addFilter(StdErrFilter())
            err_handler.setFormatter(formatter)
            logger.addHandler(err_handler)
            
            # STDOUT
            out_handler = logging.StreamHandler(__stdout__)
            out_handler.addFilter(StdOutFilter())
            out_handler.setFormatter(formatter)
            logger.addHandler(out_handler)

            logger.handler_set = True

class StdErrFilter(logging.Filter):
    '''Logging filter for stderr
    '''
    def filter(self,record):
        return 1 if record.levelno >= 30 else 0

class StdOutFilter(logging.Filter):
    '''Logging filter for stdout
    '''
    def filter(self,record):
        return 1 if record.levelno <= 20 else 0

class LorisResponse(BaseResponse, CommonResponseDescriptorsMixin):
    '''Similar to Response, but IIIF Compliance Link and 
    Access-Control-Allow-Origin Headers are added and none of the
    ETagResponseMixin, ResponseStreamMixin, or WWWAuthenticateMixin 
    capabilities are included.
    See: http://werkzeug.pocoo.org/docs/wrappers/#werkzeug.wrappers.Response
    '''
    def __init__(self, response=None, status=None, content_type=None):
        super(LorisResponse, self).__init__(response=response, status=status, content_type=content_type)
        self.headers['Link'] = '<%s>;rel="profile"' % (constants.COMPLIANCE,)
        self.headers['Access-Control-Allow-Origin'] = "*"

class BadRequestResponse(LorisResponse):
    def __init__(self, message=None):
        if message is None:
            message = "Request does not match the IIIF Syntax"
        status = 400
        message = 'Bad Request: %s (%d)' % (message, status)
        super(BadRequestResponse, self).__init__(message, status, 'text/plain')

class NotFoundResponse(LorisResponse):
    def __init__(self, message):
        super(NotFoundResponse, self).__init__(message, 404, 'text/plain')

class Loris(object):

    FMT_REGEX = re.compile('^(default|color|gray|bitonal).\w{3,4}$')
    REGION_REGEX = re.compile('^(full|(pct:)?([\d.]+,){3}([\d.]+))$')
    SIZE_REGEX = re.compile('^(full|[\d.]+,|,[\d.]+|pct:[\d.]+|[\d.]+,[\d.]+|![\d.]+,[\d.]+)$')
    ROTATION_REGEX= re.compile('^(!)?([0-9.]+)$')
    def __init__(self, app_configs={ }, debug=False):
        '''The WSGI Application.
        Args:
            config ({}): 
                A dictionary of dictionaries that represents the loris.conf 
                file.
            debug (bool)
        '''
        self.app_configs = app_configs
        logger.debug('Loris initialized with these settings:')
        [logger.debug('%s.%s=%s' % (key, sub_key, self.app_configs[key][sub_key]))
            for key in self.app_configs for sub_key in self.app_configs[key]]

        self.debug = debug

        # make the loris.Loris configs attrs for easier access
        _loris_config = self.app_configs['loris.Loris']
        self.tmp_dp = _loris_config['tmp_dp']
        self.www_dp = _loris_config['www_dp']
        self.enable_caching = _loris_config['enable_caching']
        self.redirect_canonical_image_request = _loris_config['redirect_canonical_image_request']
        self.redirect_id_slash_to_info = _loris_config['redirect_id_slash_to_info']

        self.transformers = self._load_transformers()
        self.resolver = self._load_resolver()

        if self.enable_caching:
            self.info_cache = InfoCache(self.app_configs['img_info.InfoCache']['cache_dp'])
            cache_links = self.app_configs['img.ImageCache']['cache_links']
            cache_dp = self.app_configs['img.ImageCache']['cache_dp']
            self.img_cache = img.ImageCache(cache_dp,cache_links)

    def _load_transformers(self):
        tforms = self.app_configs['transforms']
        source_formats = [k for k in tforms if isinstance(tforms[k], dict)]
        logger.debug('Source formats: %s' % (repr(source_formats),))
        global_tranform_options = dict((k, v) for k, v in tforms.iteritems() if not isinstance(v, dict))
        logger.debug('Global transform options: %s' % (repr(global_tranform_options),))

        transformers = {}
        for sf in source_formats:
            # merge [transforms] options and [transforms][source_format]] options
            config = dict(self.app_configs['transforms'][sf].items() + global_tranform_options.items())
            transformers[sf] = self._load_transformer(config)
        return transformers

    def _load_transformer(self, config):
        Klass = getattr(transforms, config['impl'])
        instance = Klass(config)
        logger.debug('Loaded Transformer %s' % (config['impl'],))
        return instance

    def _load_resolver(self):
        impl = self.app_configs['resolver']['impl']
        config = self.app_configs['resolver'].copy()
        del config['impl']
        Klass = getattr(resolver,impl)
        instance = Klass(config)
        logger.debug('Loaded Resolver %s' % (impl,))
        return instance

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.route(request)
        return response(environ, start_response)


    def route(self, request):
        base_uri, ident, params, request_type = self._dissect_uri(request)

        # index.txt
        if ident == '': 
            return self.get_index(request)

        if not self.resolver.is_resolvable(ident):
            msg = "Could not resolve identifier: %s (404)" % (ident)
            return NotFoundResponse(msg)

        elif params == '':
            r = LorisResponse()
            r.headers['Location'] = '/%s/info.json' % (ident,)
            r.status_code = 303
            return r

        # pixels
        elif request_type == 'image':
            try:
                slices = params.split('/')
                info_or_quality_dot_format = slices.pop()
                quality,fmt = info_or_quality_dot_format.split('.')

                if fmt not in self.app_configs['transforms']['target_formats']:
                    return BadRequestResponse('"%s" is not a supported format' % (fmt,))
                if quality not in constants.QUALITIES:
                    return BadRequestResponse('"%s" is not a supported quality' % (quality,))

                rotation = slices.pop()
                size = slices.pop()
                region = slices.pop()

                return self.get_img(request, ident, region, size, rotation, quality, fmt)
            except ValueError:
                return BadRequestResponse('could not parse image request')
        # info
        elif request_type == 'info':
            return self.get_info(request, ident, base_uri)
            
        # favicon.ico
        elif params == 'favicon.ico':
            return self.get_favicon(request)
        else:
            return BadRequestResponse()

    def _dissect_uri(self, r):
        ident = None
        params = None
        request_type = 'info'
        # info
        if r.path.endswith('info.json'):
            ident = '/'.join(r.path[1:].split('/')[:-1])
            params = ('info.json')

        # image
        # elif r.path.split('/')[-1].split('.')[0] in ('default','color','gray','bitonal'):
        # test against rotation and size since we need to catch a bad quality here...
        elif Loris.ROTATION_REGEX.match(r.path.split('/')[-2]) and \
                Loris.SIZE_REGEX.match(r.path.split('/')[-3]) and \
                Loris.REGION_REGEX.match(r.path.split('/')[-4]):
            ident = '/'.join(r.path[1:].split('/')[:-4])
            params = '/'.join(r.path.split('/')[-4:])
            request_type = 'image'
        # bare
        else:
            ident = r.path[1:] # no leading slash
            if self.redirect_id_slash_to_info and ident.endswith('/'): 
                ident = ident[:-1]
                 # ... you're in trouble if your identifier has a trailing slash
            params = ''

        ident = quote_plus(ident)

        logger.debug('_dissect_uri ident: %s' % (ident,))
        logger.debug('_dissect_uri params: %s' % (params,))

        if r.script_root != u'':
            base_uri = '%s%s' % (r.url_root,ident)
        else:
            base_uri = '%s%s' % (r.host_url,ident)

        logger.debug('base_uri_from_request: %s' % (base_uri,))
        return (base_uri, ident, params, request_type)

    def __call__(self, environ, start_response):
        '''
        This makes Loris executable.
        '''
        return self.wsgi_app(environ, start_response)

    def get_index(self, request):
        '''
        Just so there's something at /.
        '''
        f = file(path.join(self.www_dp, 'index.txt'))
        r = Response(f, content_type='text/plain')
        if self.enable_caching:
            r.add_etag()
            r.make_conditional(request)
        return r

    def get_favicon(self, request):
        f = path.join(self.www_dp, 'icons', 'loris-icon.png')
        r = Response(file(f), content_type='image/x-icon')
        if self.enable_caching:
            r.add_etag()
            r.make_conditional(request)
        return r

    def get_info(self, request, ident, base_uri):
        r = LorisResponse()
        try:
            info, last_mod = self._get_info(ident,request,base_uri)
        except (ImageInfoException,resolver.ResolverException) as e:
            r.response = e
            r.status_code = e.http_status
            r.mimetype = 'text/plain'
        else:
            ims_hdr = request.headers.get('If-Modified-Since')

            ims = parse_date(ims_hdr)
            last_mod = parse_date(http_date(last_mod)) # see note under get_img

            if ims and ims >= last_mod:
                logger.debug('Sent 304 for %s ' % (ident,))
                r.status_code = 304
            else:
                if last_mod:
                    r.last_modified = last_mod
                # r.automatically_set_content_length
                callback = request.args.get('callback', None)
                if callback:
                    r.mimetype = 'application/javascript'
                    r.data = '%s(%s);' % (callback, info.to_json())
                else:
                    if request.headers.get('accept') == 'application/ld+json':
                        r.content_type = 'application/ld+json'
                    else:
                        r.content_type = 'application/json'
                        l = '<http://iiif.io/api/image/2/context.json>;rel="http://www.w3.org/ns/json-ld#context";type="application/ld+json"'
                        r.headers['Link'] = '%s,%s' % (r.headers['Link'], l)
                    r.data = info.to_json()
        finally:
            return r

    def _get_info(self,ident,request,base_uri,src_fp=None,src_format=None):
        if self.enable_caching:
            in_cache = ident in self.info_cache
        else:
            in_cache = False

        if in_cache:
            return self.info_cache[ident]
        else:
            if not all((src_fp, src_format)):
                # get_img can pass in src_fp, src_format because it needs them
                # elsewhere; get_info does not.
                src_fp, src_format = self.resolver.resolve(ident)

            formats = self.transformers[src_format].target_formats
            
            logger.debug('Format: %s' % (src_format,))
            logger.debug('File Path: %s' % (src_fp,))
            logger.debug('Identifier: %s' % (ident,))

            # get the info
            info = ImageInfo.from_image_file(base_uri, src_fp, src_format, formats)

            # store
            if self.enable_caching:
                self.info_cache[ident] = info
                # pick up the timestamp... :()
                info,last_mod = self.info_cache[ident]
            else:
                last_mod = None

            return (info,last_mod)
    
    def get_img(self, request, ident, region, size, rotation, quality, target_fmt):
        '''Get an Image. 
        Args:
            request (Request): 
                Forwarded by dispatch_request
            ident (str): 
                The identifier portion of the IIIF URI syntax

        '''
        r = LorisResponse()
        # ImageRequest's Parameter attributes, i.e. RegionParameter etc. are 
        # decorated with @property and not constructed until they are first 
        # accessed, which mean we don't have to catch any exceptions here.
        image_request = img.ImageRequest(ident, region, size, rotation, quality, target_fmt)

        logger.debug(image_request.request_path)

        if self.enable_caching:
            in_cache = image_request in self.img_cache
        else:
            in_cache = False

        if in_cache:
            fp = self.img_cache[image_request]
            ims_hdr = request.headers.get('If-Modified-Since')
            img_last_mod = datetime.utcfromtimestamp(path.getmtime(fp))
            # The stamp from the FS needs to be rounded using the same precision
            # as when went sent it, so for an accurate comparison turn it into
            # an http date and then parse it again :-( :
            img_last_mod = parse_date(http_date(img_last_mod))
            logger.debug("Time from FS (default, rounded): " + str(img_last_mod))
            logger.debug("Time from IMS Header (parsed): " + str(parse_date(ims_hdr)))
            # ims_hdr = parse_date(ims_hdr) # catch parsing errors?
            if ims_hdr and parse_date(ims_hdr) >= img_last_mod:
                logger.debug('Sent 304 for %s ' % (fp,))
                r.status_code = 304
                return r
            else:
                r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
                r.status_code = 200
                r.last_modified = img_last_mod
                r.headers['Content-Length'] = path.getsize(fp)
                r.response = file(fp)

                # resolve the identifier
                src_fp, src_format = self.resolver.resolve(ident)
                # hand the Image object its info
                info = self._get_info(ident, request, src_fp, src_format)[0]
                image_request.info = info
                # we need to do the above to set the canonical link header

                canonical_uri = '%s%s' % (request.url_root, image_request.c14n_request_path)
                r.headers['Link'] = '%s,<%s>;rel="canonical"' % (r.headers['Link'], canonical_uri,)


                return r
        else:
            try:

                # 1. Resolve the identifier
                src_fp, src_format = self.resolver.resolve(ident)

                # 2. Hand the Image object its info
                info = self._get_info(ident, request, src_fp, src_format)[0]
                image_request.info = info

                # 3. Check that we can make the quality requested
                if image_request.quality not in info.profile[1]['qualities']:
                    return BadRequestResponse('"%s" quality is not available for this image' % (image_request.quality,))

                # 4. Redirect if appropriate
                if self.redirect_canonical_image_request:
                    if not image_request.is_canonical:
                        logger.debug('Attempting redirect to %s' % (image_request.c14n_request_path,))
                        r.headers['Location'] = image_request.c14n_request_path
                        r.status_code = 301
                        return r

                # 5. Make an image
                fp = self._make_image(image_request, src_fp, src_format)
                
            except (resolver.ResolverException, ImageInfoException, 
                img.ImageException, RegionSyntaxException, 
                RegionRequestException, SizeSyntaxException,
                SizeRequestException, RotationSyntaxException) as e:
                r.response = e
                r.status_code = e.http_status
                r.mimetype = 'text/plain'
                return r

        r.content_type = constants.FORMATS_BY_EXTENSION[target_fmt]
        r.status_code = 200
        r.last_modified = datetime.utcfromtimestamp(path.getctime(fp))
        r.headers['Content-Length'] = path.getsize(fp)
        canonical_uri = '%s%s' % (request.url_root, image_request.c14n_request_path)
        r.headers['Link'] = '%s,<%s>;rel="canonical"' % (r.headers['Link'], canonical_uri,)
        r.response = file(fp)

        if not self.enable_caching:
            r.call_on_close(unlink(fp))

        return r

    def _make_image(self, image_request, src_fp, src_format):
        '''
        Args:
            image_request (img.ImageRequest)
            src_fp (str)
            src_format (str)
        Returns:
            (str) the fp of the new image
        '''
        # figure out paths, make dirs
        if self.enable_caching:
            p = path.join(self.img_cache.cache_root, Loris._get_uuid_path())
            target_dp = path.dirname(p)
            target_fp = '%s.%s' % (p, image_request.format)
            if not path.exists(target_dp):
                makedirs(target_dp)
        else:
            # random str
            n = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
            target_fp = '%s.%s' % (path.join(self.tmp_dp, n), image_request.format)

        logger.debug('Target fp: %s' % (target_fp,))

        # Get the transformer
        transformer = self.transformers[src_format]

        transformer.transform(src_fp, target_fp, image_request)
        #  cache if caching (this makes symlinks for next time)
        if self.enable_caching:
            self.img_cache[image_request] = target_fp

        return target_fp

    @staticmethod
    def _get_uuid_path():
        # Make a pairtree-like path from a uuid
        # Wonder if this should be time.time() plus some random check chars,
        # just to make it shorter
        _id = uuid.uuid1().hex
        return path.sep.join([_id[i:i+2] for i in range(0, len(_id), 2)])


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    extra_files = []

    project_dp = path.dirname(path.dirname(path.realpath(__file__)))
    conf_fp = path.join(project_dp, 'etc', 'loris.conf')
    extra_files.append(conf_fp)

    app = create_app(debug=True, debug_jp2_transformer='kdu') # or 'opj'

    run_simple('localhost', 5004, app, use_debugger=True, use_reloader=True,
        extra_files=extra_files)
