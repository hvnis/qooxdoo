<?xml version="1.0"?>
<!-- **************************************************************************
*
*  qooxdoo - the new era of web development
*
*  http://qooxdoo.org
*
*  Copyright:
*    2007 1&1 Internet AG, Germany, http://www.1and1.org
*
*  License:
*    LGPL: http://www.gnu.org/licenses/lgpl.html
*    EPL: http://www.eclipse.org/org/documents/epl-v10.php
*    See the LICENSE file in the project's top-level directory for details.
*
*  Authors:
*    * Thomas Herchenroeder (thron7)
*
**************************************************************************** -->
<!-- **************************************************************************
* NAME
*  mk-doc2admin-json.xsl -  transform qooxdoo Makefile XML to qooxdoo BuildTool
*                           JSON
*  
* SYNTAX
*  xsltproc mk-doc2admin-json.xsl <file>.xml
*  
*  <file>.xml  - An XML file of the format as generated by
*                tool/make/makefile_doc.py
*  
* DESCRIPTION
*  This XSLT transforms the XML representing qooxdoo makefile contents into JSON
*  as used by BuildTool. The XML is usually generated by makefile_doc.py.
*
* SEE ALSO
*    makefile_doc.py
**************************************************************************** -->

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

	<xsl:output omit-xml-declaration="yes"/>

  <xsl:template match="mak">
    <xsl:text>{label: '', type: 'mak', items: [&#xa;</xsl:text>
    <xsl:for-each select="part">
      <xsl:call-template name="part"/>
      <xsl:if test="not(last()=position())">
        <xsl:text>,</xsl:text>
      </xsl:if>
    </xsl:for-each>
    <xsl:text>]}</xsl:text>
  </xsl:template>

  <xsl:template match="part" name="part">
		<xsl:param name="Indent"/>
    <xsl:text>&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>{label: '</xsl:text>
    <xsl:value-of select="normalize-space(string(title))"/>
    <xsl:text>',&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>type: 'part',&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>id: '</xsl:text>
    <xsl:number count="*" level="multiple"/>  <!-- 'id' set here -->
    <xsl:text>',&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>items: [</xsl:text>
    <xsl:for-each select="section">
      <xsl:call-template name="section">
        <xsl:with-param name="Indent" select="concat($Indent,'  ')"/>
      </xsl:call-template>
      <xsl:if test="not(last()=position())">
        <xsl:text>,</xsl:text>
      </xsl:if>
    </xsl:for-each>
    <xsl:text>&#xa;</xsl:text>
    <xsl:for-each select="incl">
      <xsl:call-template name="incl">
        <xsl:with-param name="Indent" select="concat($Indent,'  ')"/>
      </xsl:call-template>
      <xsl:if test="not(last()=position())">
        <xsl:text>,</xsl:text>
      </xsl:if>
    </xsl:for-each>
    <xsl:text>&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>]}</xsl:text>
  </xsl:template>

  <xsl:template name="section" match="section">
		<xsl:param name="Indent"/>
    <xsl:text>&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>{label: '',&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>type: 'section',&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>id: '</xsl:text>
    <xsl:number count="*" level="multiple"/>  <!-- 'id' set here -->
    <xsl:text>',&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>desc: '</xsl:text>
    <xsl:value-of select="normalize-space(string(descr))"/>
    <xsl:text>',</xsl:text>
    <xsl:text>&#xa;</xsl:text>
    <xsl:value-of select="$Indent"/>
    <xsl:text>items:[</xsl:text>
    <xsl:for-each select="var">
      <xsl:call-template name="var">
        <xsl:with-param name="Indent" select="concat($Indent,'  ')"/>
      </xsl:call-template>
      <xsl:if test="not(last()=position())">
        <xsl:text>,</xsl:text>
      </xsl:if>
    </xsl:for-each>
    <xsl:text>]}</xsl:text>
  </xsl:template>

  <xsl:template name="var" match="var">
    <xsl:text>{label: '</xsl:text>
    <xsl:value-of select="name"/> 
    <xsl:text>',id: '</xsl:text>
    <xsl:number count="*" level="multiple"/>  <!-- 'id' set here -->
    <xsl:text>', type: 'var', defaultt: '</xsl:text>
    <xsl:value-of select="default"/> 
    <xsl:text>'}</xsl:text>
  </xsl:template>

  <xsl:template name="incl" match="incl">
    <xsl:text>{label: '</xsl:text>
    <xsl:value-of select="."/> 
    <xsl:text>', type: 'incl'}</xsl:text>
  </xsl:template>
  
</xsl:stylesheet>
