from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'guacamole.views.index'),
    url(r'^tunnel/$', 'guacamole.views.tunnel'),

    url(r'^admin/', include(admin.site.urls)),
)
