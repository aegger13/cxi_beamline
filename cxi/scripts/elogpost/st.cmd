source /reg/g/pcds/setup/pathmunge.sh

export EPICS_CA_MAX_ARRAY_BYTES=8000000
export PSPKG_ROOT=/reg/g/pcds/pkg_mgr

export PSPKG_RELEASE="cxi-3.1.0"
source $PSPKG_ROOT/etc/set_env.sh

## Override any packages with development versions here ##
pythonpathmunge /reg/g/pcds/pyps/cxi/dev

if [ "$LOCAL_PYTHONPATH" != "" ] ; then
    pythonpathmunge $LOCAL_PYTHONPATH
fi

python elogpost.py
