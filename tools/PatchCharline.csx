// PatchCharline.csx -- 放大引擎的换行宽度，抵消我们加宽字距后"每行少放 3 个字"。
//
// 引擎换行上限 = charline * hspace(8) 像素。我们的汉字步进是 17（原版 14），
// 所以同样一行少放 ~3 个字，才会出现"第二行就一个字"。把 charline 按比例放大，
// 每行字数就回到原版水平：
//     33 -> 43   (264 -> 344px)   普通框，能放 20 个汉字
//     26 -> 37   (208 -> 296px)   有头像，能放 17 个（原版这里只有 208px，最容易被折）
//     37 -> 49   (296 -> 392px)   战斗框，能放 23 个
//     29 -> 39   (232 -> 312px)   战斗+头像，能放 18 个
//
// `originalcharline == 33` 这类判断必须一起改，否则赋值改了、判断还在比 33，
// 逻辑就断了。
//
// Environment: PATCH_OUT  输出文件
using System; using System.IO; using System.Linq; using System.Collections.Generic;
using UndertaleModLib; using UndertaleModLib.Models;
using Underanalyzer.Decompiler; using UndertaleModLib.Compiler;

string outp = Environment.GetEnvironmentVariable("PATCH_OUT");
var pairs = new (string Old, string New)[] { ("33", "43"), ("26", "37"), ("37", "49"), ("29", "39") };
// 只碰这些上下文里的数字，避免误改别的常数
string[] lenses = { "charline", "charline_face", "originalcharline" };

var global = new GlobalDecompileContext(Data);
var group = new CompileGroup(Data);
int total = 0;
foreach (var c in Data.Code.Where(x => x.ParentEntry == null && x.Instructions != null
                                       && x.Instructions.Count > 0).ToList())
{
    string gml;
    try { gml = new DecompileContext(global, c).DecompileToString(); }
    catch { continue; }
    if (!lenses.Any(l => gml.Contains(l))) continue;
    string orig = gml;
    int n = 0;
    foreach (var (oldV, newV) in pairs)
    {
        // 赋值：charline = 33;  /  charline_face = 26;
        foreach (var name in new[] { "charline", "charline_face" })
        {
            string a = $"{name} = {oldV};", b = $"{name} = {newV};";
            int k = 0, i = 0;
            while ((i = gml.IndexOf(a, i)) >= 0) { k++; i += a.Length; }
            if (k > 0) { gml = gml.Replace(a, b); n += k; }
        }
        // 判断：originalcharline == 33  /  charline == 33
        foreach (var name in new[] { "originalcharline", "charline" })
        {
            string a = $"{name} == {oldV}", b = $"{name} == {newV}";
            int k = 0, i = 0;
            while ((i = gml.IndexOf(a, i)) >= 0) { k++; i += a.Length; }
            if (k > 0) { gml = gml.Replace(a, b); n += k; }
        }
    }
    if (n > 0) { group.QueueCodeReplace(c, gml); total += n;
        Console.WriteLine($"  {c.Name.Content}: {n} 处"); }
}
Console.WriteLine($"合计 {total} 处");
if (total == 0) return;
var res = group.Compile();
Console.WriteLine($"汇编成功={res.Successful}");
if (res.Errors != null) foreach (var e in res.Errors.Take(6)) Console.WriteLine("   错误: " + e);
if (!res.Successful) return;
using (var fs = File.Create(outp)) UndertaleIO.Write(fs, Data);
Console.WriteLine("已写出 " + outp);
