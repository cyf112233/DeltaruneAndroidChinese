// PatchHardcodedStrings.csx -- translate UI text that is baked into the STRG
// chunk instead of being looked up through the language JSON.
//
// Environment:
//   HARDCODED_MAP   JSON object { "<exact source string>": "<translation>" }
//   FONT_OUT        where to save the modified data file
//
// GameMaker stores strings in a table where the SAME string can be referenced
// from many places, so replacing by content (rather than by index) is both
// simpler and safer.  Occurrences that are not found are reported but are not
// an error: the launcher and each chapter hold different subsets.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UndertaleModLib;
using UndertaleModLib.Models;

string mapPath = Environment.GetEnvironmentVariable("HARDCODED_MAP");
string outPath = Environment.GetEnvironmentVariable("FONT_OUT");
if (string.IsNullOrEmpty(mapPath) || string.IsNullOrEmpty(outPath))
{
    Console.WriteLine("ERROR: HARDCODED_MAP and FONT_OUT must be set");
    return;
}

var map = JObject.Parse(File.ReadAllText(mapPath));
int replaced = 0, notFound = 0;

foreach (var pair in map)
{
    string src = pair.Key;
    string dst = (string)pair.Value;
    bool hit = false;
    foreach (var s in Data.Strings)
    {
        if (s?.Content == src)
        {
            s.Content = dst;
            replaced++;
            hit = true;
        }
    }
    if (!hit)
    {
        notFound++;
        string shown = src.Length > 50 ? src.Substring(0, 50) : src;
        Console.WriteLine("NOTFOUND " + shown.Replace("\n", "\\n"));
    }
}

Console.WriteLine($"STRG replaced={replaced} notFound={notFound}");
if (replaced > 0)
{
    using (var fs = File.Create(outPath))
        UndertaleIO.Write(fs, Data);
    Console.WriteLine("WROTE " + outPath);
}
else
{
    Console.WriteLine("nothing replaced; no output written");
}
