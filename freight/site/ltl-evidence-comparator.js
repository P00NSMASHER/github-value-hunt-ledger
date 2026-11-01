/* RETALLY: locally computed LTL reweigh evidence comparator.
 * No network, browser storage, third-party calculation or NMFC class estimate.
 * One identical handling-unit type per comparison. Source: NMFTA help, March 2026.
 */
(function () {
  "use strict";
  const MAX_UNITS = 1000;
  const MAX_INCHES = 1200;
  const MAX_POUNDS = 200000;

  function positiveNumber(value, label, max, wholeNumber) {
    const raw = String(value === undefined || value === null ? "" : value).trim();
    const number = Number(raw);
    if (!raw || !Number.isFinite(number) || number <= 0 || number > max ||
        (wholeNumber && !Number.isInteger(number))) {
      throw new RangeError(label + " must be a positive " + (wholeNumber ? "whole number" : "number") +
        " up to " + max + ".");
    }
    return number;
  }

  function measure(unit, name, count) {
    if (!unit || typeof unit !== "object") throw new RangeError(name + " measurements are missing.");
    const l = positiveNumber(unit.length, name + " length", MAX_INCHES, false);
    const w = positiveNumber(unit.width, name + " width", MAX_INCHES, false);
    const h = positiveNumber(unit.height, name + " height", MAX_INCHES, false);
    const perWeight = positiveNumber(unit.weight, name + " gross weight", MAX_POUNDS, false);
    const volume = l * w * h * count / 1728;
    const weight = perWeight * count;
    const density = weight / volume;
    if (![volume, weight, density].every(Number.isFinite) || volume <= 0) {
      throw new RangeError(name + " figures are out of range.");
    }
    return {volume: volume, weight: weight, density: density};
  }

  function compare(input) {
    if (!input || typeof input !== "object") throw new RangeError("Comparison figures are missing.");
    const count = positiveNumber(input.count, "Handling unit count", MAX_UNITS, true);
    const original = measure(input.original, "Original", count);
    const carrier = measure(input.carrier, "Carrier-revised", count);
    return {
      count: count, original: original, carrier: carrier,
      change: {
        weight: carrier.weight - original.weight,
        volume: carrier.volume - original.volume,
        density: carrier.density - original.density
      }
    };
  }

  // Export pure arithmetic for the pinned, network-free Node regression tests.
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {compare: compare, positiveNumber: positiveNumber};
  }

  if (typeof document === "undefined") return;
  const byId = function (id) { return document.getElementById(id); };
  const form = byId("ltlCompareForm");
  if (!form) return;

  function rawFigures(prefix) {
    return {
      length: byId(prefix + "Length").value,
      width: byId(prefix + "Width").value,
      height: byId(prefix + "Height").value,
      weight: byId(prefix + "Weight").value
    };
  }
  function clearResult() {
    byId("ltlCompareError").textContent = "";
    byId("ltlCompareResults").hidden = true;
  }
  function display(value, signed) {
    const numeric = Math.abs(value) < 0.005 ? 0 : value;
    return (signed && numeric > 0 ? "+" : "") + numeric.toFixed(2);
  }
  function render(output) {
    const fields = [
      ["ltlOriginalTotalWeight", output.original.weight],
      ["ltlCarrierTotalWeight", output.carrier.weight],
      ["ltlWeightDifference", output.change.weight],
      ["ltlOriginalCube", output.original.volume],
      ["ltlCarrierCube", output.carrier.volume],
      ["ltlCubeDifference", output.change.volume],
      ["ltlOriginalDensity", output.original.density],
      ["ltlCarrierDensity", output.carrier.density],
      ["ltlDensityDifference", output.change.density]
    ];
    fields.forEach(function (field) {
      byId(field[0]).textContent = display(field[1], /Difference$/.test(field[0]));
    });
    const sentence = "The recorded values differ by " +
      display(output.change.weight, true) + " lb gross weight, " +
      display(output.change.volume, true) + " cubic feet and " +
      display(output.change.density, true) + " PCF. ";
    byId("ltlResultSummary").textContent = sentence +
      "These are unverified measurements, not proof of a freight class, billing error or realized recovery.";
    byId("ltlCompareResults").hidden = false;
  }
  function calculate() {
    try {
      const result = compare({
        count: byId("ltlUnits").value,
        original: rawFigures("ltlOriginal"),
        carrier: rawFigures("ltlCarrier")
      });
      byId("ltlCompareError").textContent = "";
      render(result);
    } catch (error) {
      byId("ltlCompareResults").hidden = true;
      byId("ltlCompareError").textContent = error instanceof RangeError ?
        error.message : "Unable to compare figures. Review the numbers entered.";
    }
  }
  form.addEventListener("submit", function (event) { event.preventDefault(); calculate(); });
  form.addEventListener("input", clearResult);
  byId("ltlDemo").addEventListener("click", function () {
    const sample = {
      ltlUnits: 1,
      ltlOriginalLength: 48, ltlOriginalWidth: 40,
      ltlOriginalHeight: 45, ltlOriginalWeight: 450,
      ltlCarrierLength: 48, ltlCarrierWidth: 40,
      ltlCarrierHeight: 48, ltlCarrierWeight: 500
    };
    Object.keys(sample).forEach(function (id) { byId(id).value = String(sample[id]); });
    clearResult();
    calculate();
  });
  byId("ltlClear").addEventListener("click", function () {
    form.reset();
    clearResult();
  });
  byId("ltlPrint").addEventListener("click", function () { window.print(); });
}());
