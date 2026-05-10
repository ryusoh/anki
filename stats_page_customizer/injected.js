(function () {
  if (window.statsCustomizerInterval)
    clearInterval(window.statsCustomizerInterval);
  document.documentElement.dataset.statsCustomizer = "active";

  window.__scSixMonthMode = window.__scSixMonthMode || false;
  window.__scActivating = window.__scActivating || false;

  // ======= ONE-TIME SETUP: Fetch interceptor =======
  if (!window.__scFetchPatched) {
    window.__scFetchPatched = true;
    var origFetch = window.fetch;
    window.__scActiveFetches = 0;
    window.__scOnFetchComplete = null;

    window.fetch = function (url, opts) {
      window.__scActiveFetches++;
      var fetchPromise;

      if (
        window.__scSixMonthMode &&
        opts &&
        opts.method === "POST" &&
        opts.body
      ) {
        var u = typeof url === "string" ? url : "";
        if (u.includes("graph") || u.includes("Graph")) {
          if (typeof Blob !== "undefined" && opts.body instanceof Blob) {
            var self = this;
            var args = arguments;
            fetchPromise = opts.body.arrayBuffer().then(function (buf) {
              try {
                var modified = patchProtobufDays(new Uint8Array(buf), 182);
                return origFetch.call(
                  self,
                  url,
                  Object.assign({}, opts, { body: modified }),
                );
              } catch (e) {
                return origFetch.apply(self, args);
              }
            });
          } else {
            try {
              var modified = patchProtobufDays(opts.body, 182);
              if (modified !== opts.body) {
                fetchPromise = origFetch.call(
                  this,
                  url,
                  Object.assign({}, opts, { body: modified }),
                );
              }
            } catch (e) {}
            if (!fetchPromise) fetchPromise = origFetch.apply(this, arguments);
          }

          fetchPromise = fetchPromise.then(function (res) {
            if (res && typeof res.arrayBuffer === "function") {
              return res.arrayBuffer().then(function (buf) {
                try {
                  buf = patchGraphsResponse(buf, 182);
                } catch (e) {}
                var init = { status: res.status, statusText: res.statusText };
                if (res.headers) init.headers = res.headers;
                return new Response(buf, init);
              });
            }
            return res;
          });
        }
      }

      if (!fetchPromise) fetchPromise = origFetch.apply(this, arguments);

      var finalize = function (res) {
        window.__scActiveFetches--;
        if (window.__scActiveFetches <= 0) {
          window.__scActiveFetches = 0;
          if (window.__scOnFetchComplete) {
            var cb = window.__scOnFetchComplete;
            window.__scOnFetchComplete = null;
            setTimeout(cb, 50);
          }
        }
        return res;
      };
      return fetchPromise.then(finalize, function (err) {
        finalize(null);
        throw err;
      });
    };
  }

  // ======= ONE-TIME SETUP: Math.min patch =======
  if (!window.__scMathMinPatched) {
    window.__scMathMinPatched = true;
    var origMin = Math.min;
    Math.min = function () {
      if (window.__scSixMonthMode && arguments.length === 2) {
        var a = arguments[0],
          b = arguments[1];
        if (a === 70 && b > 70 && b <= 183 && Number.isInteger(b)) return b;
        if (b === 70 && a > 70 && a <= 183 && Number.isInteger(a)) return a;
      }
      return origMin.apply(this, arguments);
    };
  }

  // ======= Protobuf helpers =======

  function decodeVarint(arr, offset) {
    var val = 0,
      shift = 0,
      i = offset,
      b;
    do {
      b = arr[i++];
      if (shift < 31) val += (b & 0x7f) << shift;
      else val += (b & 0x7f) * Math.pow(2, shift);
      shift += 7;
    } while (b & 0x80 && i < arr.length);
    return { value: val | 0, next: i };
  }

  function patchGraphsResponse(buf, maxDays) {
    var arr = new Uint8Array(buf),
      i = 0;
    while (i < arr.length) {
      var tagRes = decodeVarint(arr, i),
        tag = tagRes.value,
        fieldNum = tag >>> 3,
        wireType = tag & 0x07;
      i = tagRes.next;
      if (wireType === 2) {
        var lenRes = decodeVarint(arr, i),
          len = lenRes.value;
        i = lenRes.next;
        if (fieldNum === 7 || fieldNum === 8 || fieldNum === 9) {
          var endField = i + len;
          while (i < endField) {
            var startSub = i,
              subTagRes = decodeVarint(arr, i),
              subTag = subTagRes.value,
              subFieldNum = subTag >>> 3,
              subWireType = subTag & 0x07;
            i = subTagRes.next;
            if (subWireType === 2) {
              var subLenRes = decodeVarint(arr, i),
                subLen = subLenRes.value;
              i = subLenRes.next;
              if (subFieldNum === 1 || subFieldNum === 2) {
                var endMap = i + subLen,
                  keyVal = 0,
                  mapI = i;
                while (mapI < endMap) {
                  var mTagRes = decodeVarint(arr, mapI),
                    mTag = mTagRes.value,
                    mNum = mTag >>> 3,
                    mWType = mTag & 0x07;
                  mapI = mTagRes.next;
                  if (mNum === 1 && mWType === 0) {
                    keyVal = decodeVarint(arr, mapI).value;
                    break;
                  } else if (mWType === 0) {
                    while (mapI < endMap && arr[mapI++] & 0x80);
                  } else if (mWType === 2) {
                    var lRes = decodeVarint(arr, mapI);
                    mapI = lRes.next + lRes.value;
                  } else if (mWType === 5) mapI += 4;
                  else if (mWType === 1) mapI += 8;
                }
                var shouldTruncate = false;
                if (fieldNum === 7 && keyVal > maxDays) shouldTruncate = true;
                if ((fieldNum === 8 || fieldNum === 9) && keyVal < -maxDays)
                  shouldTruncate = true;
                if (shouldTruncate) arr[startSub] = 0x7a;
              }
              i = endMap;
            } else if (subWireType === 0) {
              while (i < endField && arr[i++] & 0x80);
            } else if (subWireType === 5) i += 4;
            else if (subWireType === 1) i += 8;
          }
        } else i += len;
      } else if (wireType === 0) {
        while (i < arr.length && arr[i++] & 0x80);
      } else if (wireType === 5) i += 4;
      else if (wireType === 1) i += 8;
    }
    return buf;
  }

  function patchProtobufDays(body, newDays) {
    var arr;
    if (body instanceof Uint8Array) arr = body;
    else if (body instanceof ArrayBuffer) arr = new Uint8Array(body);
    else if (ArrayBuffer.isView(body))
      arr = new Uint8Array(body.buffer, body.byteOffset, body.byteLength);
    else return body;
    var i = 0,
      field2Start = -1,
      field2End = -1;
    while (i < arr.length) {
      var startI = i,
        tagRes = decodeVarint(arr, i),
        tag = tagRes.value,
        fieldNumber = tag >>> 3,
        wireType = tag & 0x07;
      i = tagRes.next;
      if (fieldNumber === 2 && wireType === 0) {
        field2Start = startI;
        while (i < arr.length && arr[i++] & 0x80);
        field2End = i;
        break;
      }
      if (wireType === 0) {
        while (i < arr.length && arr[i++] & 0x80);
      } else if (wireType === 2) {
        var lRes = decodeVarint(arr, i);
        i = lRes.next + lRes.value;
      } else if (wireType === 5) i += 4;
      else if (wireType === 1) i += 8;
      else return body;
    }
    var varint = [];
    var v = newDays;
    while (v > 0x7f) {
      varint.push((v & 0x7f) | 0x80);
      v >>>= 7;
    }
    varint.push(v & 0x7f);
    if (field2Start >= 0) {
      var result = new Uint8Array(
        field2Start + 1 + varint.length + (arr.length - field2End),
      );
      result.set(arr.subarray(0, field2Start));
      result[field2Start] = 0x10;
      for (var j = 0; j < varint.length; j++)
        result[field2Start + 1 + j] = varint[j];
      result.set(arr.subarray(field2End), field2Start + 1 + varint.length);
      return result;
    } else {
      var result = new Uint8Array(arr.length + 1 + varint.length);
      result.set(arr);
      result[arr.length] = 0x10;
      for (var j = 0; j < varint.length; j++)
        result[arr.length + 1 + j] = varint[j];
      return result;
    }
  }

  // ======= Helpers =======

  function isGraphRangeGroup(parentEl) {
    for (var v = 0; v <= 3; v++) {
      if (!parentEl.querySelector("input[type='radio'][value='" + v + "']"))
        return false;
    }
    return true;
  }

  function isTimeSeriesGraph(radioGroupParent) {
    var el = radioGroupParent;
    for (var d = 0; d < 8 && el; d++) {
      var headings = el.querySelectorAll(
        "h1, h2, h3, h4, h5, h6, .graph-title",
      );
      if (headings.length > 0) {
        for (var h = 0; h < headings.length; h++) {
          var text = headings[h].textContent || "";
          var excludes = [
            "\u9593\u9694",
            "\u6642\u9593\u5E2F",
            "\u56DE\u7B54",
            "\u6B63\u7B54\u7387",
            "Interval",
            "Hour",
            "Button",
            "Retention",
            "Answer",
          ];
          for (var e = 0; e < excludes.length; e++)
            if (text.indexOf(excludes[e]) >= 0) return false;
        }
        return true;
      }
      el = el.parentElement;
    }
    return true;
  }

  function triggerRefetch() {
    var rangeBox = document.querySelector(".range-box");
    if (!rangeBox) return;
    var yearRadio = null,
      allRadio = null;
    var inputs = rangeBox.querySelectorAll("input[type='radio']");
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].value === "1") yearRadio = inputs[i];
      if (inputs[i].value === "2") allRadio = inputs[i];
    }
    if (!yearRadio || !allRadio) return;
    if (allRadio.checked) {
      yearRadio.click();
      setTimeout(function () {
        allRadio.click();
      }, 50);
    } else allRadio.click();
  }

  function activateSixMonthMode() {
    window.__scSixMonthMode = true;
    window.__scActivating = true;
    window.__scOnFetchComplete = null;
    var synced = document.querySelectorAll("[data-sc-synced]");
    for (var s = 0; s < synced.length; s++)
      synced[s].removeAttribute("data-sc-synced");

    triggerRefetch();
    setTimeout(function () {
      var sixLabels = document.querySelectorAll("[data-six-month-label]");
      for (var i = 0; i < sixLabels.length; i++) {
        var parent = sixLabels[i].parentElement;
        if (!parent) continue;
        var allTimeRadio = parent.querySelector(
          "input[type='radio'][value='3']",
        );
        if (allTimeRadio) {
          window.__scActivating = true;
          allTimeRadio.click();
          window.__scActivating = false;
        }
      }
      var sixRadios = document.querySelectorAll("[data-six-month-radio]");
      for (var j = 0; j < sixRadios.length; j++) {
        sixRadios[j].checked = true;
        var p = sixRadios[j].parentElement;
        if (p && p.parentElement) {
          var others = p.parentElement.querySelectorAll(
            "input[type='radio']:not([data-six-month-radio])",
          );
          for (var k = 0; k < others.length; k++) others[k].checked = false;
        }
      }
      window.__scActivating = false;
    }, 300);
  }

  function deactivateSixMonthMode(clickedRadio) {
    window.__scSixMonthMode = false;
    var sixRadios = document.querySelectorAll("[data-six-month-radio]");
    for (var i = 0; i < sixRadios.length; i++) sixRadios[i].checked = false;
    var synced = document.querySelectorAll("[data-sc-synced]");
    for (var s = 0; s < synced.length; s++)
      synced[s].removeAttribute("data-sc-synced");

    var graphTitle = "",
      clickedValue = clickedRadio ? clickedRadio.value : "";
    if (clickedRadio) {
      var el = clickedRadio;
      for (var i = 0; i < 8 && el; i++) {
        var h = el.querySelector(".graph-title, h1, h2, h3, h4, h5, h6");
        if (h) {
          graphTitle = (h.textContent || "").trim();
          break;
        }
        el = el.parentElement;
      }
    }

    var restored = false;
    var executeRestore = function () {
      if (restored) return;
      restored = true;
      if (!graphTitle || clickedValue === "") return;
      var allRadios = document.querySelectorAll(
        "input[type='radio'][value='" + clickedValue + "']",
      );
      for (var i = 0; i < allRadios.length; i++) {
        var r = allRadios[i],
          el = r,
          foundMatch = false;
        for (var d = 0; d < 8 && el; d++) {
          var h = el.querySelector(".graph-title, h1, h2, h3, h4, h5, h6");
          if (h && (h.textContent || "").trim() === graphTitle) {
            foundMatch = true;
            break;
          }
          el = el.parentElement;
        }
        if (foundMatch) {
          window.__scActivating = true;
          r.click();
          var container = r;
          for (var c = 0; c < 8 && container; c++) {
            var siblingRadios = container.querySelectorAll(
              "input[type='radio']",
            );
            if (siblingRadios.length >= 4) {
              for (var j = 0; j < siblingRadios.length; j++)
                siblingRadios[j].checked =
                  siblingRadios[j].value === clickedValue;
              break;
            }
            container = container.parentElement;
          }
          window.__scActivating = false;
          break;
        }
      }
    };

    var rangeBox = document.querySelector(".range-box");
    if (rangeBox) {
      var yearRadio = null,
        allRadio = null;
      var inputs = rangeBox.querySelectorAll("input[type='radio']");
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].value === "1") yearRadio = inputs[i];
        if (inputs[i].value === "2") allRadio = inputs[i];
      }
      if (yearRadio && allRadio) {
        if (allRadio.checked) {
          window.__scOnFetchComplete = function () {
            window.__scOnFetchComplete = executeRestore;
            allRadio.click();
          };
          yearRadio.click();
        } else {
          window.__scOnFetchComplete = executeRestore;
          allRadio.click();
        }
      }
    }

    // Fallback: guarantee executeRestore runs even if __scOnFetchComplete
    // never fires (e.g. range-box click didn't trigger a fetch).
    setTimeout(executeRestore, 500);
  }

  // ======= Main DOM manipulation =======
  function applyChanges() {
    if (window.__scSixMonthMode) {
      var activeSixRadios = document.querySelectorAll("[data-six-month-radio]");
      for (var i = 0; i < activeSixRadios.length; i++) {
        if (!activeSixRadios[i].checked) activeSixRadios[i].checked = true;
        var p = activeSixRadios[i].parentElement;
        if (p && p.parentElement) {
          var nativeOthers = p.parentElement.querySelectorAll(
            "input[type='radio']:not([data-six-month-radio])",
          );
          for (var k = 0; k < nativeOthers.length; k++)
            if (nativeOthers[k].checked) nativeOthers[k].checked = false;
        }
      }
    }

    var rangeBox = document.querySelector(".range-box");
    if (rangeBox) {
      var rbLabels = rangeBox.querySelectorAll("label");
      var rbYearLabel = null,
        rbAllLabel = null;
      for (var ri = 0; ri < rbLabels.length; ri++) {
        var inp = rbLabels[ri].querySelector("input[type='radio']");
        if (!inp) continue;
        if (inp.value === "1") rbYearLabel = rbLabels[ri];
        if (inp.value === "2") rbAllLabel = rbLabels[ri];
      }
      if (rbYearLabel && rbYearLabel.style.display !== "none")
        rbYearLabel.style.display = "none";
      if (rbAllLabel) {
        var allInp = rbAllLabel.querySelector("input[type='radio']");
        if (allInp && !allInp.checked) allInp.click();
        if (rbAllLabel.style.display !== "none")
          rbAllLabel.style.display = "none";
        if (rbAllLabel.parentElement) {
          var vis = Array.from(
            rbAllLabel.parentElement.querySelectorAll("label"),
          ).filter(function (l) {
            return l.style.display !== "none";
          });
          if (vis.length === 0) rbAllLabel.parentElement.style.display = "none";
        }
      }
    }

    var allLabelsForHide = document.querySelectorAll("label");
    for (var i = 0; i < allLabelsForHide.length; i++) {
      var l = allLabelsForHide[i],
        radio0 = l.querySelector("input[type='radio'][value='0']");
      if (radio0) {
        var el = l,
          isIntervals = false;
        for (var d = 0; d < 8 && el; d++) {
          var headings = el.querySelectorAll(
            "h1, h2, h3, h4, h5, h6, .graph-title",
          );
          if (headings.length > 0) {
            for (var h = 0; h < headings.length; h++) {
              var text = headings[h].textContent || "";
              if (
                text.indexOf("\u9593\u9694") >= 0 ||
                text.indexOf("Interval") >= 0
              ) {
                isIntervals = true;
                break;
              }
            }
            break;
          }
          el = el.parentElement;
        }
        if (isIntervals && l.style.display !== "none") {
          l.style.display = "none";
          if (radio0.checked) {
            var parentGrp = l.parentElement;
            if (parentGrp) {
              var r1 = parentGrp.querySelector(
                "input[type='radio'][value='1']",
              );
              if (r1) r1.click();
            }
          }
        }
      }
    }

    var allLabels = document.querySelectorAll(
      "label:not([data-six-month-label])",
    );
    for (var ti = 0; ti < allLabels.length; ti++) {
      var label = allLabels[ti];
      if (label.closest && label.closest(".range-box")) continue;
      if (label.getAttribute("data-six-month-added")) continue;
      var inp = label.querySelector("input[type='radio']");
      if (!inp || inp.value !== "1") continue;
      var parent = label.parentElement;
      if (!parent || !isGraphRangeGroup(parent) || !isTimeSeriesGraph(parent))
        continue;

      label.setAttribute("data-six-month-added", "true");
      var sixLabel = document.createElement("label");
      sixLabel.setAttribute("data-six-month-label", "true");
      var sixRadio = document.createElement("input");
      sixRadio.type = "radio";
      sixRadio.setAttribute("data-six-month-radio", "true");
      if (inp.name) sixRadio.name = inp.name;
      sixLabel.appendChild(sixRadio);
      sixLabel.appendChild(document.createTextNode(" 6\u304B\u6708"));
      label.after(sixLabel);

      sixRadio.addEventListener(
        "change",
        (function (radio) {
          return function () {
            activateSixMonthMode();
            setTimeout(function () {
              radio.checked = true;
            }, 350);
          };
        })(sixRadio),
      );

      var nativeRadios = parent.querySelectorAll(
        "input[type='radio']:not([data-six-month-radio])",
      );
      for (var ni = 0; ni < nativeRadios.length; ni++) {
        if (nativeRadios[ni].getAttribute("data-sc-deact")) continue;
        nativeRadios[ni].setAttribute("data-sc-deact", "true");
        nativeRadios[ni].addEventListener(
          "click",
          function () {
            if (window.__scSixMonthMode && !window.__scActivating)
              deactivateSixMonthMode(this);
          },
          true,
        );
      }

      if (window.__scSixMonthMode) {
        if (!parent.getAttribute("data-sc-synced")) {
          parent.setAttribute("data-sc-synced", "true");
          var allTimeRadio = parent.querySelector(
            "input[type='radio'][value='3']",
          );
          if (allTimeRadio) {
            window.__scActivating = true;
            allTimeRadio.click();
            allTimeRadio.checked = false;
            window.__scActivating = false;
          }
        }
        sixRadio.checked = true;
      }
    }
  }

  applyChanges();
  window.statsCustomizerInterval = setInterval(applyChanges, 200);
})();
