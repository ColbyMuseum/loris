![loris icon](www/icons/loris-icon-name.png?raw=true) Loris IIIF Image Server
=============================================================================

__If you're looking for a stable version, please use the [latest release](https://github.com/pulibrary/loris/releases/tag/1.2.2). The development branch is working toward [IIIF Image API 2.0](http://iiif.io/api/image/2.0/).__

[![Build Status](https://travis-ci.org/pulibrary/loris.png)](https://travis-ci.org/pulibrary/loris.png)

Demos
-----
 * [Mentelin Bible, l. 1r](http://libimages.princeton.edu/loris/pudl0001%2F5138415%2F00000011.jp2/full/full/0/default.jpg) (link is broken until PUL is running IIIF 2.0 instance. See [here](http://libimages.princeton.edu/loris/pudl0001%2F5138415%2F00000011.jp2/full/full/0/native.jpg) for 1.1 compliant demo image)
 * [Serving Images for OpenSeadragon](http://libimages.princeton.edu/osd-demo)

Installation Instructions
-------------------------
These instructions are known to work on Ubuntu 12.04 or greater and Python 2.6.3 or greater (but less than 3.0.0). See below for some help with RedHat/CentOS and Debian.

**Do Not!** Run `setup.py` until you've read the following:

 * [Install Dependencies](doc/dependencies.md)
 * [Configuration Options](doc/configuration.md)
 * [Cache Maintenance](doc/cache_maintenance.md)
 * [Resolver Implementation](doc/resolver.md)
 * [Run `setup.py`](doc/setup.md)
 * [Deploy with Apache](doc/apache.md)
 * [Deploy with Docker](docker/README.md)
 * (Optional) [Developer Notes](doc/develop.md)

You're best off working through these steps in order.


RedHat, Debian and Troubleshooting
---------------------------------
[mmcclimon](https://github.com/mmcclimon) has provided some excellent [instructions for deploying Loris on RedHat 6 or the equivalent CentOS](doc/redhat-install.md). 

If you're running Debian and/or run into any pitfalls with the steps above, [Regis Robineau](https://github.com/regisrob) of the [Biblissima Project](http://www.biblissima-condorcet.fr/) has created an [excellent set of instructions](http://doc.biblissima-condorcet.fr/loris-setup-guide-ubuntu-debian) that may help.

As always, clarifications, notes (issues, pull requests) regarding experiences on different platforms are most welcome.

IIIF 2.0 Compliance
-------------------
Loris Implements all of the IIIF Image API level 2 features, plus nearly all of the "optional" features:

 * `sizeAboveFull`
 * `rotation_arbitraty`
 * `mirroring`
 * `webp` and `gif` formats 
 
See http://iiif.io/api/image/2.0/compliance.html for details.

License
-------
### Loris
Copyright (C) 2013-4 Jon Stroop

This program is free software: you can redistribute it and/or modify it 
under the terms of the GNU General Public License as published by the Free 
Software Foundation, either version 3 of the License, or (at your option) 
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT 
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for 
more details.

You should have received a copy of the GNU General Public License along 
with this program. If not, see <http://www.gnu.org/licenses/>.

### Kakadu
#### Downloadable Executables Copyright and Disclaimer

The executables available [here](http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22) are made available for demonstration purposes only. Neither the author, Dr. Taubman, nor the University of New South Wales accept any liability arising from their use or re-distribution.

Copyright is owned by NewSouth Innovations Pty Limited, commercial arm of the University of New South Wales, Sydney, Australia. **You are free to trial these executables and even to re-distribute them, so long as such use or re-distribution is accompanied with this copyright notice and is not for commercial gain. Note: Binaries can only be used for non-commercial purposes.** If in doubt please [contact Dr. Taubman](http://www.kakadusoftware.com/index.php?option=com_content&task=blogcategory&id=8&Itemid=14).

For further details, please visit the [Kakadu website](http://www.kakadusoftware.com/)

### OpenJPEG

(Copied from http://www.openjpeg.org/BSDlicense.txt)

Copyright (c) 2002-2007, Communications and Remote Sensing Laboratory, Universite catholique de Louvain (UCL), Belgium
Copyright (c) 2002-2007, Professor Benoit Macq
Copyright (c) 2001-2003, David Janssens
Copyright (c) 2002-2003, Yannick Verschueren
Copyright (c) 2003-2007, Francois-Olivier Devaux and Antonin Descampe
Copyright (c) 2005, Herve Drolon, FreeImage Team
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS `AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.


