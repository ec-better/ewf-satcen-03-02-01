#!/bin/bash

application_path='/application'

# create the application.xml if needed
[ -d "${application_path}" ] && { 

    rm -fr ${application_path}

    [ -d "${application_path}/job" ] && rm -fr ${application_path}/job 

    mkdir -p ${application_path}/job 

    export LC_ALL="en_US.utf-8"

    $PREFIX/bin/app-gen --descriptor ${application_path}/application.xml 

    echo "#!/bin/bash" > ${application_path}/job/run.sh
    echo "source /opt/anaconda/etc/profile.d/conda.sh" >> ${application_path}/job/run.sh
    echo "conda activate $(basename $PREFIX)" >> ${application_path}/job/run.sh
    echo "$PREFIX/bin/run-node-1 " >> ${application_path}/job/run.sh

    chmod 755 ${application_path}/job/run.sh

} 

exit 0
