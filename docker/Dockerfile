FROM openjdk:8-jre-slim

RUN apt-get update && apt-get install -y wget unzip
RUN mkdir -p /opt
RUN wget "https://github.com/DescartesResearch/QPME/releases/download/2.2/qpme.product-linux.gtk.x86_64.zip" -O /opt/qpme.zip
RUN unzip /opt/qpme.zip -d /opt/
RUN mkdir -p /tmp/experiment
RUN chmod u+x /opt/qpme/SimQPN.sh
WORKDIR /opt/qpme
COPY run_experiment.sh /opt/qpme/. 
RUN chmod u+x run_experiment.sh
ENTRYPOINT ["/opt/qpme/run_experiment.sh"]
