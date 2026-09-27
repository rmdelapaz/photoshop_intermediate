// resize-folder.jsx  —  File ▸ Scripts ▸ Browse to run
var inputFolder  = Folder.selectDialog("Choose a folder of images");
if (!inputFolder) { throw new Error("No folder chosen."); }
var files = inputFolder.getFiles(/\.(jpg|jpeg|png)$/i);

for (var i = 0; i < files.length; i++) {
    var doc = app.open(files[i]);
    var longEdge = 2000;
    var scale = longEdge / Math.max(doc.width.value, doc.height.value);
    doc.resizeImage(doc.width * scale, doc.height * scale);

    var out = new File(inputFolder + "/web_" + doc.name.replace(/\.[^.]+$/, ".jpg"));
    var opt = new JPEGSaveOptions();
    opt.quality = 10;
    doc.saveAs(out, opt, true);
    doc.close(SaveOptions.DONOTSAVECHANGES);
}
alert("Done: " + files.length + " images resized.");
