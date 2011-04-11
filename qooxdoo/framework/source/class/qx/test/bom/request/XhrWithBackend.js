/* ************************************************************************

   qooxdoo - the new era of web development

   http://qooxdoo.org

   Copyright:
     2004-2011 1&1 Internet AG, Germany, http://www.1und1.de

   License:
     LGPL: http://www.gnu.org/licenses/lgpl.html
     EPL: http://www.eclipse.org/org/documents/epl-v10.php
     See the LICENSE file in the project's top-level directory for details.

   Authors:
     * Tristan Koch (tristankoch)

************************************************************************ */

/* ************************************************************************

#asset(qx/test/*)

************************************************************************ */

qx.Class.define("qx.test.bom.request.XhrWithBackend",
{
  extend : qx.dev.unit.TestCase,

  include : [qx.test.io.MRemoteTest,
             qx.dev.unit.MMock,
             qx.dev.unit.MRequirements],

  construct : function()
  {
    this.base(arguments);
  },

  members :
  {

    req : null,

    setUp: function() {
      this.require(["php"]);

      this.req = new qx.bom.request.Xhr();
    },

    tearDown: function() {
      this.req.dispose();
    },

    //
    // Basic
    //

    "test: GET": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");
      url = url + "?affe=yippie&nocache=" + Math.random();
      req.open("GET", url);

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            var data = qx.lang.Json.parse(req.responseText);
            that.assertEquals("yippie", data["affe"]);
          });
        }
      }
      req.send();

      this.wait();
    },

    "test: GET XML": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/sample.xml");

      req.open("GET", this.noCache(url));

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            that.assertObject(req.responseXML.documentElement, "Must be XML object");
          });
        }
      }
      req.send();

      this.wait();
    },

    // BUGFIX
    "test: handle arbitrary XML": function() {
      // Content-Type: foo/bar+xml
      var url = this.getUrl("qx/test/xmlhttp/xml.php");

      var req = this.req;
      req.open("GET", this.noCache(url));

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            that.assertObject(req.responseXML.documentElement, "Must be XML object");
          });
        }
      }
      req.send();

      this.wait();
    },

    "test: POST": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_post_request.php");
      req.open("POST", this.noCache(url));
      req.setRequestHeader("Content-type", "application/x-www-form-urlencoded");

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            that.assertEquals('{"affe":"true"}', req.responseText);
          });
        }
      }
      req.send("affe=true");

      this.wait();
    },

    "test: have readyState UNSENT": function() {
      var req = this.req;
      this.assertIdentical(0, req.readyState);
    },

    "test: have readyState OPENED": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_post_request.php");
      req.open("GET", this.noCache(url));

      this.assertIdentical(1, req.readyState);
    },

    // BUGFIX
    // This is a mess, see
    // http://www.quirksmode.org/blog/archives/2005/09/xmlhttp_notes_r_2.html.
    "test: progress to readyState DONE": function() {
      var req = this.req,
          states = [],
          that = this;

      req.onreadystatechange = function() {
        states.push(req.readyState);
        if (req.readyState == 4) {
          that.resume(function() {
            that.assertArrayEquals([1, 2, 3, 4], states);
          });
        }
      }

      var url = this.getUrl("qx/test/xmlhttp/echo_post_request.php");
      req.open("GET", this.noCache(url));
      req.send();

      this.wait();
    },

    // BUGFIX
    "test: progress to readyState DONE when sync": function() {
      var req = this.req,
          states = [];

      req.onreadystatechange = function() {
        states.push(req.readyState);
      }

      var url = this.getUrl("qx/test/xmlhttp/echo_post_request.php");
      req.open("GET", this.noCache(url), false);
      req.send();

      // There is no HEADERS_RECEIVED and LOADING when sync.
      // See http://www.w3.org/TR/XMLHttpRequest/#the-send-method
      this.assertArrayEquals([1, 4], states);
    },

    "test: progress to readyState DONE when from cache": function() {
      var req = this.req,
          url = this.noCache(this.getUrl("qx/test/xmlhttp/sample.html")),
          states = [],
          count = 0,
          that = this;

      req.onreadystatechange = function() {
        states.push(req.readyState);
        if (req.readyState == 4) {
          if (++count < 2) {
            // Ignore changes from previous request
            states = [];
            // From cache
            req.open("GET", url);
            req.send();
          } else {
            that.resume(function() {
              that.assertArrayEquals([1, 2, 3, 4], states);
            });
          }
        }
      }

      // Prime cache
      req.open("GET", url);
      req.send();

      this.wait();
    },

    // BUGFIX
    "test: allow many requests with same object": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");
      var count = 0;

      var that = this;
      function request() {
        req.open("GET", that.noCache(url));
        req.send();
      }

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            if (++count < 3) {
              request();
              this.wait();
            } else {
              that.assertEquals(3, count);
            }
          })
        }
      };
      request();

      this.wait();
    },

    "test: abort pending request": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");

      req.open("GET", this.noCache(url));
      req.abort();

      this.assertNotEquals(4, req.readyState, "Request must not complete");
    },

    "test: have status 200 when modified": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");

      // Make sure resource is not served from cache
      req.open("GET", this.noCache(url));

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            that.assertEquals(200, req.status);
          });
        }
      }
      req.send();

      this.wait();
    },

    // BUGFIX
    "test: have status 304 when cache is fresh": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/not_modified.php");

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            that.assertIdentical(304, req.status);
          });
        }
      }
      req.open("GET", url);

      // Pretend that client has a fresh representation of
      // this resource in its cache. Please note the ETag given
      // must be in sync with the current ETag of the file requested.
      //
      // XMLHttpRequest states:
      //
      // For 304 Not Modified responses that are a result of a user
      // agent generated conditional request the user agent must act
      // as if the server gave a 200 OK response with the appropriate
      // content. The user agent must allow setRequestHeader() to
      // override automatic cache validation by setting request
      // headers (e.g. If-None-Match or If-Modified-Since),
      // in which case 304 Not Modified responses must be passed through.
      //
      // Copied from:
      //
      // XMLHttpRequest [http://www.w3.org/TR/XMLHttpRequest/]
      // W3C Candidate Recommendation
      // Copyright © 2009 W3C® (MIT, ERCIM, Keio), All Rights Reserved.
      //

      // The actual ETag is not of importance here, since the server
      // is returning 304 anyway. We're just triggering the behavior
      // specified above.
      req.setRequestHeader("If-None-Match", "\"4893a3a-b0-49ea970349b00\"");
      req.send();

      this.wait();
    },

    // TODO: Comment out
    "test: GET simultaneously": function() {
      var count = 1,
          upTo = 20,
          startedAt = new Date(),
          duration = 0,
          that = this;

      for (var i=0; i<upTo; i++) {
        (function() {
          var req = new qx.bom.request.Xhr(),
              url = that.noCache(that.getUrl("qx/test/xmlhttp/loading.php")) + "&duration=2";

          req.onreadystatechange = function() {
            if (req.readyState != 4) {
              return;
            }

            that.resume(function() {

              // In seconds
              duration = (new Date() - startedAt) / 1000;
              that.debug("Request #" + count + " completed (" +  duration + ")");

              if (count == upTo) {
                return;
              }

              ++count;
              that.wait();
            });
          }

          req.open("GET", url);
          req.send();
        })();
      }

      // Provided two concurrent requests are made (each 6s), 20 requests
      // (i.e. 10 packs of requests) should complete after 60s
      this.wait(10000 + 1000);
    },

    //
    // onreadystatechange()
    //

    "test: call onreadystatechange for OPEN": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");

      var that = this;
      var count = 0;
      req.onreadystatechange = function() {
        // Count call for state OPENED
        if (req.readyState == 1) {
          count = count + 1;
        }

        // Assert when DONE
        if (req.readyState == 4) {
          that.resume(function() {
            // onreadystatechange should only be called
            // once for state OPENED
            that.assertEquals(1, count);
          });
        }
      };

      req.open("GET", this.noCache(url));
      req.send();

      this.wait();
    },

    "test: not call onreadystatechange when aborting OPENED": function() {
      var req = this.req;

      // OPENED, without send flag
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");
      req.open("GET", this.noCache(url));

      this.spy(req, "onreadystatechange");
      req.abort();

      this.wait(100, function() {
        this.assertNotCalled(req.onreadystatechange);
      }, this);
    },

    "test: call onreadystatechange when aborting LOADING": function() {
      var req = this.req;
      var that = this;

      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume();
        }
      }

      // Will "never" complete
      // OPENED, finally LOADING
      var url = this.getUrl("qx/test/xmlhttp/loading.php");
      req.open("GET", url + "?duration=100");
      req.send();

      window.setTimeout(function() {
        req.abort();
      }, 0);

      this.wait();
    },

    //
    // onerror()
    //

    "test: call onerror on network error": function() {
      var req = this.req;

      var that = this;
      req.onerror = function() {
        that.resume();
      }

      // Network error
      req.open("GET", "http://fail.tld");
      req.send();

      // May take a while to detect network error
      this.wait(10000);
    },

    //
    // onloadend()
    //

    "test: call onloadend on network error": function() {
      var req = this.req;

      var that = this;
      req.onloadend = function() {
        that.resume();
      }

      // Network error
      req.open("GET", "http://fail.tld");
      req.send();

      // May take a while to detect network error
      this.wait(10000);
    },

    //
    // Call order
    //

    "test: call handler in order when request successful": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/sample.html");

      var that = this;
      req.onloadend = function() {
        that.resume(function() {
          that.assertCallOrder(
            req.onreadystatechange,
            req.onload,
            req.onloadend
          );
        });
      }
      this.spy(req, "onreadystatechange");
      this.spy(req, "onload");
      this.spy(req, "onloadend");
      req.open("GET", url);
      req.send();

      this.wait();
    },

    "test: call handler in order when request failed": function() {
      var req = this.req;

      var that = this;
      req.onloadend = function() {
        that.resume(function() {
          that.assertCallOrder(
            req.onreadystatechange,
            req.onerror,
            req.onloadend
          );
        });
      }
      this.spy(req, "onreadystatechange");
      this.spy(req, "onerror");
      this.spy(req, "onloadend");
      req.open("GET", "http://fail.tld");
      req.send();

      // May take a while to detect network error
      this.wait(10000);
    },

    //
    // Disposing
    //

    // BUGFIX
    "test: dispose hard-working": function() {
      var req = this.req;
      var url = this.getUrl("qx/test/xmlhttp/echo_get_request.php");
      req.open("GET", this.noCache(url));

      var that = this;
      req.onreadystatechange = function() {
        if (req.readyState == 4) {
          that.resume(function() {
            // Must not throw error
            req.dispose();
          });
        }
      }
      req.send();

      this.wait();
    },

    noCache: function(url) {
      return url + "?nocache=" + Math.random();
    }
  }
});