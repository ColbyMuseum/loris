# TODO:
# - Parameterize python version so we can do Python 3 testing
# - Parameterize OPJ v. Kakadu

FROM ubuntu:16.04

ENV HOME /root

# Update ubuntu and install utils
RUN apt-get update -y && apt-get install -y wget git unzip

# Install pip, python, and python dependencies
RUN apt-get install -y python-dev python-setuptools python-pip
RUN pip install --upgrade pip
RUN pip2.7 install Werkzeug
RUN pip2.7 install configobj

# Correct image library paths
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/ 
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/ 
RUN ln -s /usr/lib/`uname -i`-linux-gnu/liblcms.so /usr/lib/ 
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libtiff.so /usr/lib/ 

RUN echo "/usr/local/lib" >> /etc/ld.so.conf && ldconfig

# Install image libs and Pillow
RUN apt-get install -y libjpeg8 libjpeg8-dev libfreetype6 libfreetype6-dev zlib1g-dev liblcms2-2 liblcms2-dev liblcms2-utils libtiff5-dev libssl-dev
RUN pip2.7 install attrs PyJWT cryptography
RUN pip2.7 install Pillow 

# Install cmake 3.2
WORKDIR /opt/cmake
RUN wget http://www.cmake.org/files/v3.10/cmake-3.10.2.tar.gz && tar xf cmake-3.10.2.tar.gz && cd cmake-3.10.2 && ./configure && make && make install

# Download and compile Grok tag v2.3.1
WORKDIR /opt/openjpeg
RUN git clone https://github.com/GrokImageCompression/grok.git ./
RUN git checkout tags/v2.3.1
RUN cmake -DBUILD_THIRDPARTY=bool:on -DCMAKE_BUILD_TYPE=Release . && make && make install

# Install Kakadu
WORKDIR /usr/local/lib
RUN wget --no-check-certificate https://github.com/loris-imageserver/loris/raw/development/lib/Linux/x86_64/libkdu_v74R.so \
	&& chmod 755 libkdu_v74R.so

WORKDIR /usr/local/bin
RUN wget --no-check-certificate https://github.com/loris-imageserver/loris/raw/development/bin/Linux/x86_64/kdu_expand \
	&& chmod 755 kdu_expand

# Set up and build loris

COPY ./ /opt/loris

WORKDIR /opt/loris

RUN useradd -d /var/www/loris -s /sbin/false loris
RUN mkdir /usr/local/share/images
RUN mkdir /usr/local/share/images_2

# Load example images
RUN cp -R tests/img/* /usr/local/share/images
RUN cp tests/img/jpeg_with_cmyk_profile.jpg /usr/local/share/images_2/test_cd.jpg

RUN cp etc/loris2_dev.conf etc/loris2.conf
RUN ./setup.py install

# Set loris's bind address and run
WORKDIR /opt/loris/loris

RUN sed -i -- 's/localhost/0.0.0.0/g' webapp.py
RUN sed -i 's/app = create_app(debug=True)/app = create_app(debug=False, config_file_path="..\/etc\/loris2.conf")/g' webapp.py

EXPOSE 5004
CMD ["python","webapp.py"]