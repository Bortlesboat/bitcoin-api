(function () {
  function splitTopLevel(source) {
    var tokens = [];
    var current = "";
    var quote = "";
    var escape = false;

    for (var i = 0; i < source.length; i += 1) {
      var ch = source[i];

      if (escape) {
        current += ch;
        escape = false;
        continue;
      }

      if (quote) {
        current += ch;
        if (ch === "\\") {
          escape = true;
        } else if (ch === quote) {
          quote = "";
        }
        continue;
      }

      if (ch === "'" || ch === '"') {
        quote = ch;
        current += ch;
        continue;
      }

      if (ch === "{" || ch === "}" || ch === "[" || ch === "]") {
        return null;
      }

      if (ch === ",") {
        tokens.push(current.trim());
        current = "";
        continue;
      }

      current += ch;
    }

    if (quote) {
      return null;
    }

    if (current.trim() || source.trim() === "") {
      tokens.push(current.trim());
    }

    return tokens.filter(function (token) {
      return token.length > 0;
    });
  }

  function unquote(token) {
    if (token.length < 2) {
      return token;
    }

    var quote = token[0];
    var value = token.slice(1, -1);
    if (quote === "'") {
      return value.replace(/\\\\/g, "\\").replace(/\\'/g, "'").replace(/\\"/g, '"');
    }

    try {
      return JSON.parse(token);
    } catch (error) {
      return value.replace(/\\\\/g, "\\").replace(/\\"/g, '"').replace(/\\'/g, "'");
    }
  }

  function parseSimpleArgs(source) {
    if (!source.trim()) {
      return [];
    }

    var rawTokens = splitTopLevel(source);
    if (!rawTokens) {
      return null;
    }

    var tokens = [];
    for (var i = 0; i < rawTokens.length; i += 1) {
      var token = rawTokens[i];
      if (!token) {
        continue;
      }
      if (token === "this") {
        tokens.push({ type: "self" });
        continue;
      }
      if (token === "event") {
        tokens.push({ type: "event" });
        continue;
      }
      if (/^-?\d+$/.test(token)) {
        tokens.push({ type: "number", value: Number(token) });
        continue;
      }
      if (
        (token[0] === "'" && token[token.length - 1] === "'") ||
        (token[0] === '"' && token[token.length - 1] === '"')
      ) {
        tokens.push({ type: "string", value: unquote(token) });
        continue;
      }
      return null;
    }

    return tokens;
  }

  function parseObjectLiteral(source) {
    var pairs = splitTopLevel(source);
    if (!pairs) {
      return null;
    }

    var obj = {};
    for (var i = 0; i < pairs.length; i += 1) {
      var pair = pairs[i];
      var index = pair.indexOf(":");
      if (index === -1) {
        return null;
      }

      var key = pair.slice(0, index).trim().replace(/^['"]|['"]$/g, "");
      var valueToken = pair.slice(index + 1).trim();
      if (!key) {
        return null;
      }

      if (/^-?\d+$/.test(valueToken)) {
        obj[key] = Number(valueToken);
        continue;
      }

      if (
        (valueToken[0] === "'" && valueToken[valueToken.length - 1] === "'") ||
        (valueToken[0] === '"' && valueToken[valueToken.length - 1] === '"')
      ) {
        obj[key] = unquote(valueToken);
        continue;
      }

      return null;
    }

    return obj;
  }

  function parseInvocation(rawCode) {
    if (!rawCode) {
      return null;
    }

    var code = rawCode.trim();
    var preventDefault = false;

    code = code.replace(/;?\s*return\s+false;?\s*$/i, function () {
      preventDefault = true;
      return "";
    }).trim();

    code = code.replace(/^return\s+/i, "");

    var navMatch = code.match(
      /^document\.querySelector\((['"])(.*?)\1\)\.classList\.toggle\((['"])(.*?)\3\);?$/i
    );
    if (navMatch) {
      return {
        type: "nav-toggle",
        selector: navMatch[2],
        className: navMatch[4],
        preventDefault: preventDefault,
      };
    }

    var posthogMatch = code.match(
      /^posthog\.capture\((['"])(.*?)\1\s*,\s*\{([\s\S]*)\}\);?$/i
    );
    if (posthogMatch) {
      var props = parseObjectLiteral(posthogMatch[3]);
      if (props) {
        return {
          type: "posthog-capture",
          eventName: posthogMatch[2],
          props: props,
          preventDefault: preventDefault,
        };
      }
    }

    var callMatch = code.match(/^([A-Za-z_$][\w$]*)\(([\s\S]*)\);?$/);
    if (!callMatch) {
      return null;
    }

    var args = parseSimpleArgs(callMatch[2]);
    if (args === null) {
      return null;
    }

    return {
      type: "function-call",
      name: callMatch[1],
      args: args,
      preventDefault: preventDefault,
    };
  }

  function resolveArg(arg, element, event) {
    if (arg.type === "self") {
      return element;
    }
    if (arg.type === "event") {
      return event;
    }
    return arg.value;
  }

  function invoke(parsed, element, event) {
    if (!parsed) {
      return undefined;
    }

    if (parsed.type === "nav-toggle") {
      var target = document.querySelector(parsed.selector);
      if (!target) {
        return undefined;
      }
      var isOpen = !target.classList.contains(parsed.className);
      target.classList.toggle(parsed.className);
      if (element.hasAttribute("aria-expanded")) {
        element.setAttribute("aria-expanded", isOpen ? "true" : "false");
      }
      return undefined;
    }

    if (parsed.type === "posthog-capture") {
      if (window.posthog && typeof window.posthog.capture === "function") {
        window.posthog.capture(parsed.eventName, parsed.props);
      }
      return undefined;
    }

    var fn = window[parsed.name];
    if (typeof fn !== "function") {
      return undefined;
    }

    var args = parsed.args.map(function (arg) {
      return resolveArg(arg, element, event);
    });
    return fn.apply(element, args);
  }

  function bindClick(element) {
    if (!element || element.dataset.siteHelperClickBound === "true") {
      return;
    }

    var raw = element.getAttribute("onclick");
    if (!raw) {
      return;
    }

    var parsed = parseInvocation(raw);
    if (!parsed) {
      return;
    }

    element.addEventListener("click", function (event) {
      var href = element.getAttribute("href");
      if (parsed.preventDefault || href === "#") {
        event.preventDefault();
      }

      var result = invoke(parsed, element, event);
      if (result === false) {
        event.preventDefault();
      }
    });

    element.removeAttribute("onclick");
    element.dataset.siteHelperClickBound = "true";
  }

  function bindSubmit(form) {
    if (!form || form.dataset.siteHelperSubmitBound === "true") {
      return;
    }

    var raw = form.getAttribute("onsubmit");
    if (!raw) {
      return;
    }

    var parsed = parseInvocation(raw);
    if (!parsed) {
      return;
    }

    form.addEventListener("submit", function (event) {
      var result = invoke(parsed, form, event);
      if (parsed.preventDefault || result === false) {
        event.preventDefault();
      }
    });

    form.removeAttribute("onsubmit");
    form.dataset.siteHelperSubmitBound = "true";
  }

  function collectTargets(root, selector) {
    var targets = [];
    if (!root) {
      return targets;
    }

    if (root.nodeType === 1 && root.matches(selector)) {
      targets.push(root);
    }

    if (root.querySelectorAll) {
      var matches = root.querySelectorAll(selector);
      for (var i = 0; i < matches.length; i += 1) {
        targets.push(matches[i]);
      }
    }

    return targets;
  }

  function processTree(root) {
    collectTargets(root, "[onclick]").forEach(bindClick);
    collectTargets(root, "form[onsubmit]").forEach(bindSubmit);
  }

  processTree(document);

  if (document.documentElement && typeof MutationObserver === "function") {
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i += 1) {
        var mutation = mutations[i];
        if (mutation.type === "attributes") {
          processTree(mutation.target);
          continue;
        }
        for (var j = 0; j < mutation.addedNodes.length; j += 1) {
          processTree(mutation.addedNodes[j]);
        }
      }
    });

    observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["onclick", "onsubmit"],
    });
  }
})();
