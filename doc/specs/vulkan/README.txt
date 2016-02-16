= Vulkan Specification Build Instructions and Notes =

* <<intro,Introduction>>
* <<building,Building the spec>>
* <<macros,Our asciidoc macros>>
* <<styles,Our stylesheets>>
* <<equations,Imbedding equations>>
* <<anchors,Anchors and xrefs>>
* <<depends,Software dependencies>> (general and platform-specific)
* <<history,Revision history>>

[[intro]]
== Introduction ==

This README describes important stuff for getting the Vulkan API
specification and reference pages building properly.

[[building]]
== Building The Spec ==

Assuming you have all the right tools installed (see <<depends,Software
Dependencies>> below), you should be able to go to
...path-to-git-repo/vulkan/doc/specs/vulkan and:

    $ make all

or equivalently:

    $ make xhtml chunked pdf manhtml manpdf manpages manhtmlpages checkinc checklinks

This should generate a variety of targets under $(OUTDIR) (by default,
../../../out/). The checked-in file $(OUTDIR)/index.html links to them
all, or they can individually be found as follows:

* API spec:
** Single-file XHTML (from a2x) - $(OUTDIR)/xhtml/vkspec.html
** Chunked HTML (from a2x) - $(OUTDIR)/vkspec.chunked/index.html
** PDF (from a2x) - $(OUTDIR)/pdf/vkspec.pdf
* Man pages:
** Single-file HTML - $(OUTDIR)/apispec.html
** File-per-entry-point HTML - $(OUTDIR)/man/html/*
** File-per-entry-point nroff source - $(OUTDIR)/man/3/*
* Validator output:
** List of commands, structs, etc. missing from the API spec -
   $(OUTDIR)/checks/notInSpec.txt
** Validator script output for API spec - $(OUTDIR)/checks/specErrs.txt
** Validator script output for reference pages -
   $(OUTDIR)/checks/manErrs.txt

We strongly sugges that once you have the basic build working, you use e.g.
'-j 8' (or other appropriate number depending on the number of cores in your
CPU) to parallelize the reference page builds, since there are so many of
them.

If your asciidoc installation does not put the stylesheets and xsl files in
the standard /etc/asciidoc/dblatex directory, set the environment variable
DBLATEXPREFIX to the path to that directory (the one containing the
asciidoc-dblatex.xsl and asciidoc-dblatex.sty installed with asciidoc).

[[building-test]]
=== Alternate and Test Builds ===

If you are just testing asciidoc formatting, macros, stylesheets, etc., you
can edit test.txt, which is a stripped-down version of vkspec.txt,
and build an alternate version of the spec with either

    $ make TOPDOCHTML=test.txt xhtml

or the simpler

    tmake xhtml

This example will generate the file $(OUTDIR)/xhtml/test.html . Note that
TOPDOCHTML only applies to the xhtml and chunked targets at present.

In addition to the XHTML and PDF targets, there is also a single-file HTML5
target, 'html', which generates output directly from asciidoc without going
through Docbook. This is somewhat quicker to generate, but formatting and
section numbers aren't consistent with the other builds and it is not for
publication - just testing. The 'html' target will generate the file
$(OUTDIR)/html/vkspec.html .

=== Rebuilding The Generated Images ===

There are some images in the images/ directory which are maintained in one
format but need to be converted to another format for corresponding types of
output. Most are SVG converted to PDF, some are PPT converted to PDF
converted to SVG. SVG and PDF forms are needed for the HTML and PDF output
formats, respectively.

These files are not automatically converted by the Makefile. Instead, all
output forms required are checked into images/ . On the rare occasions that
someone changes a source document and needs to regenerate the other forms,
go into images and 'make' in the directory.

[[macros]]
== Our Asciidoc Macros ==

We use a bunch of custom macros in the reference pages and API spec asciidoc
sources. The validator scripts rely on these macros as part of their sanity
checks, and you should use the macros whenever referring to an API command,
struct, token, or enum name, so the documents are semantically tagged and
more easily verifiable.

The supported macros are defined in config/vkspec.conf (for the API spec)
and config/manpages.conf (for the reference pages).

Tags used in both the specification and reference pages:

* flink:vkBlah - the name of an API command.
* fname:vkBlah - the name of an API command.
* ftext:anything - the name of something that looks like an API command, but
  isn't (wildcards like ftext:vkCmd*).
* slink:VkBlah - the name of an API C structure, handle, or scalar type. The
  slink:VkBlah.membername syntax is *not* currently supported.
* sname:VkBlah - the name of an API C structure, handle, or scalar type. The
  notation sname:VkBlah.membername is also allowed where that makes sense
  (NOTE: VkBlah.membername is *not* properly validated at present).
* stext:anything - the name of something that looks like an API structure,
  handle, or scalar type, but isn't (wildcards like stext:Vk*CreateInfo).
* elink:VkBlahFlags - the name of an API C "enum" type (bitmask or
  enumeration).
* ename:VK_BLAH - the name of an API enumeration or #define token.
* etext:anything - the name of something that looks like an API "enum" type,
  enumeration or #define token, but isn't (wildcards or partial token names,
  like etext:BC5).
* pname:param - the name of a command parameter or struct member being
  documented
* basetype:type - the name of a base scalar type, such as basetype:VkBool32.
* code:varname - the name of a shading language variable

Tags used only in the specification, at present:

* can:, cannot:, may:, maynot:, must:, mustnot:, optional:, recommend:,
  required:, should:, and shouldnot: - used to tag places in the spec where
  these terms are used in accordance with their definitions in section 1.3
  "Terminology". They do not currently do anything but expand to their names
  (adding a space for e.g. mustnot: -> must not), but may be used to
  generate an index or some visual indicator in the future.

The [efs]link: macros are used for validation, and are also expanded into
xref links to the correspondingly named anchor.

The [efsp]name: macros are used for validation, but are *not* expanded into
links.

The [efs]text: macros are not used for validation, and are not expanded into
links.

We will eventually tool up the spec and ref pages to the point that anywhere
there's a type or token referred to, you could click/hover on it in the HTML
view and be taken to the definition of that type/token. That will take some
more plumbing work to tag the stuff in the autogenerated include files, and
do something sensible in the spec (e.g. resolve links to internal
references).

In that light, the [fs]name: vs. [fs]link: distinction seems mostly
unneeded. Probably the only time we would not want a tag to be a link to its
definition is when tagging a function name inside its own ref page. So once
the plumbing is done, most of the [fs]name: tags can turn into [fs]link:
tags.

The ename: vs. elink: distinction is different since they're referring to
different namespaces - individual enumerant names vs. "enum" type names -
rather than different ways of presenting the same command or struct name as
for the other tags.

Most of these macros deeply need more intuitive names.

[[styles]]
== Our stylesheets ==

NOTE: Section mostly TBD.

This branch introduces a Vulkan-specific XHTML CSS stylesheet
in config/vkspec-xhtml.css. Mostly it just clones the default
Asciidoc stylesheet, but adds some new features:

=== Marking Changes ===

There is the start of support for marking added, removed, and changed text
in the spec body. Currently this is supported *only* in the XHTML targets
('xhtml' and 'chunked'), and *only* for paragraphs and spans of words.

Added, removed, and changed material is marked with the asciidoc *roles*
named _added_, _removed_, and _changed_ respectively. They can be used to
mark an entire paragraph, as follows:

    [role="change"]
    This paragraph shows change markings.

Or a few words in a sentence, as follows:

    This sentence contains [added]#some added words# and [removed]#some
    removed words#.

The formatting of these roles text depends on the stylesheet. Currently it
all three roles are red text, and the "removed" role is also strike-through
text.

=== Marking Normative Language ===

There is support for marking normative language in the document. Currently
this is supported *only* in the XHTML targets ('xhtml' and 'chunked').

Normative language is marked with the asciidoc *role* named _normative_.
It can be used to mark entire paragraphs or spans of words, in the
same fashion as change markings (described above). In addition, the
normative terminology macros, such as must: and may: and cannot:,
always use this role.

The formatting of normative language depends on the stylesheet. Currently it
just comes out in purple. There will be some way to turn this on or off at
build time shortly.

[[equations]]
== Imbedding Equations

Equations should be written using the latexmath: inline and block macros.
The contents of the latexmath: blocks should be LaTeX math notation,
surrounded by appropriate delimiters - pass:[$$], +++\[\\]+++, pass:[\(\)],
or pass:[\begin{env}/\end{env}] math environments such as pass:[{equation*}]
or pass:[{align*}].

The asciidoc macros and configuration files, as well as the dblatex
customization layers, have been modified significantly so that LaTeX math is
passed through unmodified to all HTML output forms (using the MathJax engine
for real-time rendering of equations) and to dblatex for PDF output.

The following caveats apply:

* The special characters < > & can currently be used only in
  +++[latexmath]+++ block macros, not in +++latexmath:[]+++ inline macros.
  Instead use \lt for < and \gt for >. & is an alignment construct for
  multiline equations, and should only appear in block macros anyway.
* AMSmath environments (e.g. pass:[\begin{equation*}], pass:[{align*}],
  etc.) can be used, to the extent MathJax supports them.
* When using AMSmath environments, do *not* also surround the equation block
  with +++\[\\]+++ brackets. That is not legal LaTeX math and will break the
  PDF build. It is good practice to make sure all spec targets build
  properly before proposing a merge to master.
* Arbitrary LaTeX constructs cannot be used with MathJax. It is an equation
  renderer, not an full LaTeX engine. So imbedding stuff like \Large or
  pass:[\hbox{\tt\small VK\_FOO}] does not work in any of the HTML backends
  and should be avoided.

[[anchors]]
== Asciidoc Anchors And Xrefs

In the API spec, sections can have anchors (labels) applied with the
following syntax. In general the anchor should immediately precede the
chapter or section title and should use the form
'+++[[chapter-section-label]]+++'. For example,

For example, in chapter 'synchronization.txt':

++++
[[synchronization-primitives]]
Synchronization Primitives
++++

Cross-references to those anchors can then be generated with, for example,

++++
See the <<synchronization-primitives>> section for discussion
of fences, semaphores, and events.
++++

You can also add anchors on arbitrary paragraphs, using a similar naming
scheme.

Anything whose definition comes from one of the autogenerated API include
files ({protos,flags,enums,structs}/*.txt) has a corresponding anchor whose
name is the name of the function, struct, etc. being defined. Therefore you
can say something like:

    Fences are used with the +++<<vkQueueSubmit>>+++ command...

[[depends]]
== Software Dependencies ==

This section describes the software components used by the Vulkan spec
toolchain. under the <<depends-general,General Dependencies>> below, then
describes specific considerations for Windows environments using Cygin under
<<depends-cygwin,Cygwin Dependencies>>

[[depends-general]]
=== General Dependencies ===

These are versions of required tools in Jon's development environment
(Debian 8, shown as Debian package names). Earlier versions *may* work but
unless they are verified by someone else, there's no way to know that. Later
versions should work.

  - GNU make (make version: 4.0.8-1; older versions probably OK)
  - Asciidoc / a2x (asciidoc version: 8.6.9-3)
  - Python 3 (python, version: 3.4.2)
  - Python LXML library (python-lxml, version: 3.4.0-1)
  - Git command-line client (git, version: 2.1.4)
    Only needed if regenerating specversion.txt. Any version supporting the
    operations 'git symbolic-ref --short HEAD' and 'git log -1
    --format="%H"' should work).
  - Docbook LaTeX toolchain (dblatex, version: 0.3.5-2)
  - Source code highlighter (source-highlight, version: 3.1.7-1+b1)
  - LaTeX distribution (texlive, version: 2014.20141024-2)

[[depends-cygin]]
=== Cygwin Dependencies ===

The cygwin installer is at http://www.cygwin.org. Use the 64-bit version,
because the 32-bit version does not include the latest version of asciidoc
required for this project.

Required Cygwin packages (current version):

* Devel/make (4.1-1)
* Python/python (2.7.10-1) - Needed for asciidoc toolchain
* Python/python3 (3.4.3-1)
* Python/python3-lxml (3.4.4-1) - Needed for generating vulkan.h
* Text/asciidoc (8.6.8-1)
* Text/dblatex (0.3.4-1)
* Text/source-highlight (3.1.8-1)

Optional Cygwin packages (current version):

* Devel/gcc-core (4.9.3-1) - Needed for validating generated headers
* Devel/gcc-g++ (4.9.3-1) - Needed for validating generated headers
* Devel/git (2.5.1-1) - Needed for updating specversion.txt

[[history]]
== Revision History

* 2015/11/11 - Add new can: etc. macros and DBLATEXPREFIX variable.
* 2015/09/21 - Convert document to asciidoc and rename to README.md
  in the hope the gitlab browser will render it in some fashion.
* 2015/09/21 - Add descriptions of LaTeX+MathJax math support for all
  output formats.
* 2015/09/02 - Added Cygwin package info
* 2015/09/02 - Initial version documenting macros, required toolchain
  components and versions, etc.


