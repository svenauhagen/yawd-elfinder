from django.db import models
from django.forms import CharField
from connector import ElfinderConnector

class ElfinderFile(object):
    """
    This class represents an Elfinder file.
    """
    
    def __init__(self, hash_, optionset):
        self.hash = hash_
        self.optionset = optionset
        self._info = None
    
    def _get_info(self):
        if self._info is None:
            
            if not self.hash:
                self._info = {}
            else:
                try:
                    from conf import settings as ls

                    connector = ElfinderConnector(ls.ELFINDER_CONNECTOR_OPTION_SETS[self.optionset])
                    info = connector.execute('info', targets = [self.hash], options=True)['files'][0]
                        
                    #get image dimensions
                    if 'mime' in info and info['mime'].startswith('image'):
                        info['dim'] = connector.execute('dim', target=self.hash)['dim']
                        
                    #calculate thumbnail url
                    if 'tmb' in info and 'tmbUrl' in info:
                        info['tmb'] = '%s%s' % (info['tmbUrl'], info['tmb'])
                        del info['tmbUrl']
                            
                    #`url` key is the equivelant `rootUrl` of the elfinderwidget
                    if 'url' in info: 
                        info['rootUrl'] = info['url']
                        del info['url']
                        
                    if 'archivers' in info:
                        del info['archivers']
                        
                    if 'extract' in info:
                        del info['extract']
    
                    self._info = info
                except:
                    from django.utils.translation import ugettext as _
                    self._info = { 'error' : _('This file is no longer valid') }  

        return self._info
        
    @property
    def url(self):
        """
        Get the file url
        """
        info = self._get_info()
        return '%s%s' % (info['rootUrl'], '/'.join(info['path'].split(info['separator'])[1:])) if info else ''
    
    @property
    def info(self):
        """
        Returns:
            a **dictionary** holding information about the file, 
            as returned by the volume driver.
        """
        return self._get_info()
            
    def __unicode__(self):
        return self.hash

class ElfinderFormField(CharField):
    """
    Override the standard CharField form field
    to set :class:`elfinder.widgets.ElfinderWidget` as the default widget.
    """
    
    def __init__(self, optionset, start_path, *args, **kwargs):
        from widgets import ElfinderWidget
        super(ElfinderFormField, self).__init__(*args, **kwargs)
        #TODO: elfinder widget should be initialized using possible client options from model field declaration
        self.optionset = optionset 
        self.widget = ElfinderWidget(optionset, start_path)
        
    def to_python(self, value):
        """
        Convert ``value`` to an :class:`elfinder.fields.ElfinderFile` object.
        """
        if isinstance(value, ElfinderFile):
            return value
        return ElfinderFile(hash_=value, optionset=self.optionset)
    
    def clean(self, value):
        """
        Override the default CharField validation to validate the 
        ElfinderFile hash string before converting it to an ElfinderField
        object. Finally, return a cleaned ElfinderFile object.  
        """
        self.validate(value)
        self.run_validators(value)
        value = self.to_python(value)
        return value

class ElfinderField(models.Field):
    """
    Custom model field holding an :class:`elfinder.fields.ElfinderFile` object.
    """
    
    description = "An elfinder file model field."
    __metaclass__ = models.SubfieldBase

    def __init__(self, optionset='default', start_path=None, *args, **kwargs):
        self.optionset = optionset
        self.start_path = start_path

        if not 'max_length' in kwargs:
            kwargs['max_length'] = 100 #default field length

        super(ElfinderField, self).__init__(*args, **kwargs)
        
    def get_internal_type(self):
        """
        This lets Django know how to handle the field
        """
        return "CharField"
        
    def to_python(self, value):
        """
        Convert ``value`` to an :class:`elfinder.fields.ElfinderFile` object.
        """
        if isinstance(value, ElfinderFile):
            return value
        return ElfinderFile(hash_=value, optionset=self.optionset)
    
    def get_prep_value(self, value):
        """
        Overriden method to return a string representation of 
        the :class:`elfinder.fields.ElfinderFile`.
        """
        if isinstance(value, ElfinderFile):
            return value.hash
        return value
    
    def get_prep_lookup(self, lookup_type, value):
        """
        Overriden method to disallow 
        ``year``, ``month`` and ``day`` queries
        """
        if lookup_type in ['year', 'month', 'day']:
            raise TypeError('Lookup type %r not supported.' % lookup_type)
        
        return super(ElfinderField, self).get_prep_lookup(lookup_type, value)
        
    def formfield(self, **kwargs):
        """
        Overriden method to set the form field defaults.
        See :class:`elfinder.fields.ElfinderFormField`
        """
        
        defaults = {
                'form_class': ElfinderFormField,
                'optionset' : self.optionset,
                'start_path' : self.start_path
        }
        defaults.update(kwargs)
        return super(ElfinderField, self).formfield(**defaults)