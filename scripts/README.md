HTML Diff Script for Vulkan
===========================

This is a first cut at a script to compare Vulkan HTML specifications. Usage
is simply 'htmldiff file1.html file2.html > diff.html'. The script does not
copy CSS and images requires by the input specs, so it's best to generate
the output in the same directory as one of the inputs.

The scripts used require Python and Perl. Additionally, the python
'utidylib' module and the underlying libtidy C library are required,
which may make it challenging to run the scripts on non-Linux platforms
- I haven't checked and those requirements cannot be easily removed. On
Debian Linux, it may be necessary to install the 'python-utidylib' and
'libtidy' packages if they are not already present. I haven't checked
dependencies for other Linux distributions but they are probably
similar.

The scripts are taken from the code backing the

    http://services.w3.org/htmldiff

website. 'htmldiff' is the Python driver script. 'htmldiff.pl' is the
Perl script which generates the diff after preprocessing of the input
HTML by 'htmldiff'. 'htmldiff.orig' is the original Python script from
the website, modified to run at the command line instead of as a CGI
script.
