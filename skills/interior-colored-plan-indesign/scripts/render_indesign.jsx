/* Native A3 colored-plan renderer. Compile a validated job with prepare_job.py.
   Input coordinates are top-left points of normalized_plan.pdf; all scale uniformly.
   This renderer consumes reviewed paths; it never infers spaces from PDF graphics.
*/
(function () {
    if (typeof CP_JOB === 'undefined') throw Error('Compile a job with prepare_job.py first.');
    var J = CP_JOB;
    // Enforce the picker boundary before any access to InDesign application state.
    if (!(J.styles instanceof Array) || !J.styles.length) throw Error('Validated styles are required.');
    if (J.mode !== 'demo' && J.mode !== 'final' && J.mode !== 'template') throw Error('Unknown production mode.');
    var maintenance = J.mode === 'demo' && J.fictional_fixture === true && J.library_maintenance === true && !J.source;
    if (J.fictional_fixture === true && !maintenance) throw Error('Fictional fixtures are only for source-free library maintenance.');
    if (J.mode === 'demo' && !maintenance) {
        if (!J.source || J.project_demo_requested !== true || typeof J.demo_request_evidence !== 'string' || !/\S/.test(J.demo_request_evidence))
            throw Error('Show cached style options first; project demos need an explicit user request.');
    }
    if (J.mode === 'final') {
        if (!J.source || J.styles.length !== 1 || !J.selection || J.selection.confirmed !== true ||
            J.selection.style_id !== J.styles[0].id || typeof J.selection.evidence !== 'string' || !/\S/.test(J.selection.evidence) || J.geometry_reviewed !== true)
            throw Error('A real user selection and one reviewed project style are required.');
    }
    if (J.mode === 'template' && J.source) throw Error('Blank templates cannot contain a project source.');
    var out = Folder(J.output_dir);
    if (!out.exists) throw Error('Output folder is missing.');
    var oldUI = app.scriptPreferences.userInteractionLevel;
    var oldUnit = app.scriptPreferences.measurementUnit;
    var oldPdfPage = app.pdfPlacePreferences.pageNumber;
    var oldPdfCrop = app.pdfPlacePreferences.pdfCrop;
    var oldPdfBg = app.pdfPlacePreferences.transparentBackground;
    var oldJpeg = app.jpegExportPreferences.properties;
    var oldPdfExport = app.pdfExportPreferences.properties;
    var doc = null, MM = 72 / 25.4, problems = [], stats = [];
    function mm(x) { return x * MM; }
    function write(file, str) {
        var f = File(out.fsName + '/' + file); f.encoding = 'UTF-8'; f.open('w'); f.write(str); f.close();
    }
    function quote(s) { return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\r/g, '\\r').replace(/\n/g, '\\n').replace(/\t/g, '\\t') + '"'; }
    function serialize(v) {
        if (v === null || typeof v === 'undefined') return 'null';
        if (typeof v === 'string') return quote(v);
        if (typeof v === 'number' || typeof v === 'boolean') return String(v);
        var a = [], k;
        if (v instanceof Array) { for (k = 0; k < v.length; k++) a.push(serialize(v[k])); return '[' + a.join(',') + ']'; }
        for (k in v) if (v.hasOwnProperty(k)) a.push(quote(k) + ':' + serialize(v[k]));
        return '{' + a.join(',') + '}';
    }
    function layer(name) { var l = doc.layers.itemByName(name); return l.isValid ? l : doc.layers.add({name:name}); }
    function color(hex) {
        var name = 'CP_' + hex.replace('#', ''), c = doc.colors.itemByName(name);
        if (c.isValid) return c;
        return doc.colors.add({name:name, model:ColorModel.PROCESS, space:ColorSpace.RGB,
            colorValue:[parseInt(hex.substr(1,2),16),parseInt(hex.substr(3,2),16),parseInt(hex.substr(5,2),16)]});
    }
    function rect(pg,l,b,fill,stroke,weight) {
        var o=pg.rectangles.add(l,{geometricBounds:b,fillColor:fill?color(fill):doc.swatches.itemByName('None'),
            strokeColor:stroke?color(stroke):doc.swatches.itemByName('None'),strokeWeight:weight||0});
        return o;
    }
    function oval(pg,l,b,fill,stroke,weight) {
        return pg.ovals.add(l,{geometricBounds:b,fillColor:fill?color(fill):doc.swatches.itemByName('None'),
            strokeColor:stroke?color(stroke):doc.swatches.itemByName('None'),strokeWeight:weight||0});
    }
    function line(pg,l,a,b,col,weight) {
        var o=pg.graphicLines.add(l,{strokeColor:color(col),strokeWeight:weight});
        o.paths[0].entirePath=[a,b]; return o;
    }
    function poly(pg,l,pts,fill,stroke,weight) {
        var o=pg.polygons.add(l,{fillColor:fill?color(fill):doc.swatches.itemByName('None'),
            strokeColor:stroke?color(stroke):doc.swatches.itemByName('None'),strokeWeight:weight||0});
        o.paths[0].entirePath=pts; return o;
    }
    var font = null;
    function text(pg,l,b,str,size,col,align,bold) {
        var t=pg.textFrames.add(l,{geometricBounds:b,contents:str});
        t.textFramePreferences.insetSpacing=0;
        t.textFramePreferences.verticalJustification=VerticalJustification.TOP_ALIGN;
        t.parentStory.appliedFont=font;
        t.parentStory.pointSize=size;
        t.parentStory.leading=size*1.4;
        t.parentStory.fillColor=color(col);
        t.parentStory.justification=align||Justification.LEFT_ALIGN;
        t.parentStory.hyphenation=false;
        return t;
    }
    function autoHeight(t) {
        t.textFramePreferences.autoSizingReferencePoint=AutoSizingReferenceEnum.TOP_LEFT_POINT;
        t.textFramePreferences.useNoLineBreaksForAutoSizing=false;
        t.textFramePreferences.autoSizingType=AutoSizingTypeEnum.HEIGHT_ONLY;
        doc.recompose();
    }
    function badge(pg,l,x,y,id,col,size) {
        var r=mm(size||2.9);
        var circ=oval(pg,l,[y-r,x-r,y+r,x+r],col,'#FFFFFF',0.5);
        circ.label='room-badge:'+id;
        var t=text(pg,l,[y-r,x-r,y+r,x+r],id,9,'#FFFFFF',Justification.CENTER_ALIGN);
        t.textFramePreferences.verticalJustification=VerticalJustification.CENTER_ALIGN;
        t.parentStory.leading=9;
        t.label='room-number:'+id;
    }
    function shadow(o,strength,soft) {
        var s=o.transparencySettings.dropShadowSettings;
        s.mode=ShadowMode.DROP; s.blendMode=BlendMode.MULTIPLY;
        s.effectColor=color('#222222'); s.opacity=strength;
        s.xOffset=mm(soft?0.5:1.8); s.yOffset=mm(soft?0.8:2.5); s.size=mm(soft?1:2);
        s.noise=0; s.spread=0;
    }
    function inside(x,y,pts) {
        var flag=false;
        for(var i=0,k=pts.length-1;i<pts.length;k=i++) {
            var a=pts[i],b=pts[k];
            if(((a[1]>y)!=(b[1]>y))&&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])) flag=!flag;
        }
        return flag;
    }
    function contains(a,value) {for(var i=0;i<a.length;i++)if(a[i]===value)return true;return false;}
    function hatch(pg,l,zone,map,s) {
        // Fixture-only native patterns. Real materials use reviewed texture_image frames.
        var p=zone.polygon,loX=1e9,loY=1e9,hiX=-1e9,hiY=-1e9,i,x,y;
        for(i=0;i<p.length;i++){loX=Math.min(loX,p[i][0]);loY=Math.min(loY,p[i][1]);hiX=Math.max(hiX,p[i][0]);hiY=Math.max(hiY,p[i][1]);}
        if(zone.material==='wood') {
            for(x=loX+12;x<hiX;x+=18) for(y=loY+8;y<hiY-8;y+=80) {
                var yy=Math.min(y+72,hiY-8);
                if(inside(x,y,p)&&inside(x,yy,p)) line(pg,l,map([x,y]),map([x,yy]),'#C8B89C',0.35);
            }
        } else if(zone.material==='stone') {
            for(x=loX+36;x<hiX-24;x+=58) for(y=loY+32;y<hiY-20;y+=53) {
                if(inside(x-8,y,p)&&inside(x+9,y+5,p)) line(pg,l,map([x-8,y]),map([x+9,y+5]),'#D5D1C8',0.3);
            }
        } else {
            for(x=loX+15;x<hiX-8;x+=17) for(y=loY+15;y<hiY-8;y+=17) {
                if(inside(x,y,p)) {var c=map([x,y]); oval(pg,l,[c[1]-.4,c[0]-.4,c[1]+.4,c[0]+.4],'#C8C8BD',null,0);}
            }
        }
    }
    function plan(pg,S,box) {
        var w=J.coordinate_size[0],h=J.coordinate_size[1];
        var sc=Math.min(box[2]/w,box[3]/h),xx=box[0]+(box[2]-w*sc)/2,yy=box[1]+(box[3]-h*sc)/2;
        function P(p){return [xx+p[0]*sc,yy+p[1]*sc];}
        function B(b){var p=P(b);return [p[1],p[0],p[1]+b[3]*sc,p[0]+b[2]*sc];}
        var floor=layer('02 地坪与材质'),effect=layer('03 投影与强化'),srcLayer=layer('04 PDF线稿'),detail=layer('05 家具与绿植'),numbers=layer('06 空间编号');
        var i,z,o,fill,pts;
        rect(pg,floor,[yy-mm(4),xx-mm(4),yy+h*sc+mm(4),xx+w*sc+mm(4)],S.bg,null,0);
        for(i=0;i<J.zones.length;i++) {
            z=J.zones[i];pts=[];for(var k=0;k<z.polygon.length;k++)pts.push(P(z.polygon[k]));
            fill=S.floor;
            if(S.id==='A1')fill=z.material==='wood'?S.secondary:(z.material==='carpet'?'#E2E3D9':S.floor);
            if(S.id==='B3')fill=i%3===0?S.secondary:S.floor;
            if(S.id==='C1')fill=z.environment?S.secondary:S.floor;
            if(S.id==='D1'||S.id==='D2')fill=S.floor;
            o=poly(pg,floor,pts,fill,null,0);o.label='zone:'+(z.room_id||i);
            if(z.opacity!==undefined)o.fillTransparencySettings.blendingSettings.opacity=z.opacity;
            if(z.texture_image){o.place(File(z.texture_image));o.fit(FitOptions.FILL_PROPORTIONALLY);}
            else if(S.id==='A1'&&J.fictional_fixture)hatch(pg,floor,z,P,S);
        }
        for(i=0;i<J.emphasis.length;i++) {
            z=J.emphasis[i];if(z.style_ids&&!contains(z.style_ids,S.id))continue;
            pts=[];for(var k=0;k<z.polygon.length;k++)pts.push(P(z.polygon[k]));
            o=poly(pg,floor,pts,S.accent,null,0);
            o.fillTransparencySettings.blendingSettings.opacity=z.opacity||55;
            o.label='emphasis:'+(z.role||i);
        }
        if(J.source) {
            app.pdfPlacePreferences.pageNumber=1;
            app.pdfPlacePreferences.pdfCrop=PDFCrop.CROP_MEDIA;
            app.pdfPlacePreferences.transparentBackground=true;
            var fr=rect(pg,srcLayer,[yy,xx,yy+h*sc,xx+w*sc],null,null,0);
            fr.place(File(J.source.path));fr.fit(FitOptions.PROPORTIONALLY);fr.fit(FitOptions.CENTER_CONTENT);
            // Neutral source lines over original native fills. White PDF objects still require visual review.
            fr.transparencySettings.blendingSettings.blendMode=BlendMode.MULTIPLY;
            fr.label='locked-pdf-source';
        }
        for(i=0;i<J.walls.length;i++) {
            z=J.walls[i];o=line(pg,effect,P(z.a),P(z.b),S.wall,(z.width||7)*sc);
            o.label='wall-enhancement:'+i;
            if(S.id==='D1')shadow(o,50,false);
            else if(S.id==='D2')shadow(o,24,true);
            else if(S.id==='A1')shadow(o,18,true);
            else if(S.id==='C1')shadow(o,22,false);
        }
        for(i=0;i<J.lines.length;i++) {z=J.lines[i];line(pg,detail,P(z.a),P(z.b),z.color||'#9A9C9A',(z.width||1)*sc);}
        for(i=0;i<J.furniture.length;i++) {
            z=J.furniture[i];var b=B(z.bounds);
            if(z.shape==='plant') {
                o=oval(pg,detail,b,S.green,null,0);
                o.transparencySettings.blendingSettings.opacity=65;
                var cx=(b[1]+b[3])/2,cy=(b[0]+b[2])/2,r=(b[3]-b[1])*.25;
                oval(pg,detail,[cy-r,cx-r,cy+r,cx+r],S.green,null,0);
                if(S.id==='A1'||S.id==='C1')shadow(o,16,true);
            } else {
                fill=z.accent&&S.id==='A1'?S.secondary:S.furniture;
                var stroke=S.id==='E1'?S.accent:'#AAAAA4';
                o=z.shape==='ellipse'?oval(pg,detail,b,fill,stroke,0.35):rect(pg,detail,b,fill,stroke,0.35);
                if(z.round){o.topLeftCornerOption=o.topRightCornerOption=o.bottomLeftCornerOption=o.bottomRightCornerOption=CornerOptions.ROUNDED_CORNER;
                    o.topLeftCornerRadius=o.topRightCornerRadius=o.bottomLeftCornerRadius=o.bottomRightCornerRadius=mm(.8);}
                if(S.id==='A1')shadow(o,15,true);
            }
            o.label='furniture:'+i;
        }
        for(i=0;i<J.rooms.length;i++) {
            var r=J.rooms[i],a=P(r.anchor),badgeColor=S.id==='E1'?S.accent:(r.secondary?'#8A94BC':'#244EA1');
            if(r.leader) {var e=P(r.leader);line(pg,numbers,a,e,badgeColor,.5);}
            badge(pg,numbers,a[0],a[1],r.id,badgeColor,2.9);
        }
        return {scale_pt_per_source_pt:sc,placed_bounds_pt:[yy,xx,yy+h*sc,xx+w*sc],source_size:J.coordinate_size};
    }
    function legend(pg,x,y,width,S) {
        var l=layer('07 版式与功能表');
        text(pg,l,[y-mm(13),x,y-mm(4),x+width],'功能空间  /  SPACE INDEX',10,'#313A45');
        line(pg,l,[x,y-mm(2)],[x+width,y-mm(2)],'#B9C3D0',.6);
        var cursor=y+mm(5),rows=[];
        for(var i=0;i<J.rooms.length;i++) {
            var r=J.rooms[i],t;
            badge(pg,l,x+mm(3),cursor+mm(3),r.id,S.id==='E1'?S.accent:(r.secondary?'#8A94BC':'#244EA1'),2.9);
            t=text(pg,l,[cursor-mm(.5),x+mm(10),cursor+mm(9),x+width],r.name,11,'#30363A');
            t.label='legend-name:'+r.id;
            autoHeight(t);
            var height=t.geometricBounds[2]-t.geometricBounds[0];
            if(r.name_en){
                var en=text(pg,l,[cursor+height+mm(1),x+mm(10),cursor+height+mm(9),x+width],r.name_en,7.5,'#8D949A');
                autoHeight(en);height+=mm(1)+en.geometricBounds[2]-en.geometricBounds[0];
            }
            var rowH=Math.max(mm(16),height+mm(6));rows.push({id:r.id,name:r.name,y_pt:cursor,height_pt:rowH});cursor+=rowH;
            if(t.geometricBounds[3]>x+width+.1)problems.push('Legend frame exceeds fixed width: '+r.id);
        }
        if(cursor>mm(238))problems.push('Legend exceeds available height; split plan/legend across A3 pages.');
        return rows;
    }
    function pageHeader(pg,S,index) {
        var l=layer('07 版式与功能表');
        text(pg,l,[mm(14),mm(18),mm(24),mm(275)],J.title,19,'#263443');
        text(pg,l,[mm(27),mm(18),mm(36),mm(287)],J.subtitle||'FLOOR PLAN  /  平面规划',9,'#79838D');
        text(pg,l,[mm(15),mm(304),mm(25),mm(402)],J.mode==='template'?'A3 版式 · 未选风格':S.id+'  '+S.name,12,'#263443');
        text(pg,l,[mm(28),mm(304),mm(39),mm(402)],J.mode==='demo'?'风格小样 · 待选择':(J.mode==='template'?'A3 版式模板':'已选风格 · 精细彩平'),8.5,'#79838D');
        line(pg,l,[mm(18),mm(43)],[mm(402),mm(43)],'#C4CBD1',.5);
        line(pg,l,[mm(18),mm(276)],[mm(402),mm(276)],'#D5D9DC',.5);
        var note=J.fictional_fixture?'虚构平面测试样例 · 用于比较表达方法 · 参数化材质图案':(J.mode==='template'?'A3 彩平文本页模板 · 置入项目底图后按清单编排':(J.mode==='demo'?'风格小样 · 功能依据源 PDF · 待用户选择后精细制作':'彩平表达依据源 PDF；尺寸以原始图纸为准'));
        text(pg,l,[mm(280),mm(18),mm(289),mm(345)],note,7.5,'#8A9299');
        text(pg,l,[mm(280),mm(360),mm(289),mm(402)],'A3  /  '+('0'+index).slice(-2),8,'#8A9299',Justification.RIGHT_ALIGN);
    }
    try {
        app.scriptPreferences.userInteractionLevel=UserInteractionLevels.NEVER_INTERACT;
        app.scriptPreferences.measurementUnit=MeasurementUnits.POINTS;
        doc=app.documents.add(false);
        doc.documentPreferences.properties={pageWidth:mm(420),pageHeight:mm(297),facingPages:false,pagesPerDocument:J.styles.length};
        doc.viewPreferences.horizontalMeasurementUnits=doc.viewPreferences.verticalMeasurementUnits=MeasurementUnits.POINTS;
        doc.viewPreferences.rulerOrigin=RulerOrigin.PAGE_ORIGIN;
        doc.zeroPoint=[0,0];
        var names=['01 页面底色','02 地坪与材质','03 投影与强化','04 PDF线稿','05 家具与绿植','06 空间编号','07 版式与功能表'];
        for(var i=0;i<names.length;i++)layer(names[i]);
        var candidates=['PingFang SC\tRegular','Microsoft YaHei\tRegular','Source Han Sans SC\tRegular','Heiti SC\tLight','Arial Unicode MS\tRegular'];
        for(var i=0;i<candidates.length;i++){var f=app.fonts.itemByName(candidates[i]);if(f.isValid&&f.status===FontStatus.INSTALLED){font=f;break;}}
        if(!font)throw Error('No installed Chinese font found; inspect fonts before authoring.');
        for(var i=0;i<J.styles.length;i++) {
            var S=J.styles[i],pg=doc.pages[i];
            pg.label='style:'+S.id;
            rect(pg,layer('01 页面底色'),[0,0,mm(297),mm(420)],'#FFFFFF',null,0);
            pageHeader(pg,S,i+1);
            if(J.mode==='template') {
                var l=layer('07 版式与功能表');
                rect(pg,l,[mm(57),mm(18),mm(263),mm(292)],null,'#D2D8DD',.6);
                text(pg,l,[mm(147),mm(73),mm(162),mm(242)],'彩平置图区 · 等比放置源 PDF',14,'#9AA4AE',Justification.CENTER_ALIGN);
                text(pg,l,[mm(87),mm(310),mm(103),mm(402)],'编号与功能名称区',11,'#7A8590');
                text(pg,l,[mm(105),mm(310),mm(135),mm(402)],'按当前项目房间清单生成\r图内编号与此处逐项对应',9,'#9AA4AE');
            } else {
                var transform=plan(pg,S,[mm(18),mm(58),mm(274),mm(205)]);
                var rows=legend(pg,mm(310),mm(80),mm(92),S);
                stats.push({page:i+1,style:S.id,transform:transform,rooms:rows});
                if(S.tagline)text(pg,layer('07 版式与功能表'),[mm(244),mm(310),mm(264),mm(402)],S.tagline,8.5,'#8D959A');
            }
        }
        layer('04 PDF线稿').locked=true;
        doc.recompose();
        for(var i=0;i<doc.textFrames.length;i++)if(doc.textFrames[i].overflows)problems.push('Overset text: '+doc.textFrames[i].contents);
        var links=[];
        for(var i=0;i<doc.links.length;i++){
            var lk=doc.links[i];links.push({name:lk.name,status:String(lk.status),path:lk.filePath});
            if(lk.status!==LinkStatus.NORMAL&&lk.status!==LinkStatus.LINK_EMBEDDED)problems.push('Link: '+lk.name+' '+lk.status);
        }
        var fonts=[];
        for(var i=0;i<doc.fonts.length;i++){
            fonts.push({name:doc.fonts[i].name,status:String(doc.fonts[i].status)});
            if(doc.fonts[i].status!==FontStatus.INSTALLED)problems.push('Font: '+doc.fonts[i].name);
        }
        var audit={application_version:app.version,page_size_mm:[420,297],pages:doc.pages.length,font:font.name,
            mode:J.mode,fictional_fixture:!!J.fictional_fixture,styles:stats,links:links,fonts:fonts,
            problems:problems,visual_review:'required',native_reopen:'pending'};
        if(problems.length){write('audit.json',serialize(audit));throw Error(problems.join('\n'));}
        var base=out.fsName+'/'+J.name;
        doc.save(File(base+(J.mode==='template'?'.indt':'.indd')),J.mode==='template');
        doc.exportFile(ExportFormat.INDESIGN_MARKUP,File(base+'.idml'),false);
        app.pdfExportPreferences.properties={pageRange:PageRange.ALL_PAGES,exportReaderSpreads:false,
            viewPDF:false,generateThumbnails:true,includeStructure:false,exportGuidesAndGrids:false,
            cropMarks:false,bleedMarks:false,registrationMarks:false,colorBars:false,pageInformationMarks:false};
        doc.exportFile(ExportFormat.PDF_TYPE,File(base+'.pdf'),false);
        app.jpegExportPreferences.properties={exportResolution:120,jpegQuality:JPEGOptionsQuality.HIGH,
            exportingSpread:false,jpegExportRange:ExportRangeOrAllPages.EXPORT_ALL};
        doc.exportFile(ExportFormat.JPG,File(base+'.jpg'),false);
        doc.close(SaveOptions.NO);doc=null;
        var reopened=app.open(File(base+(J.mode==='template'?'.indt':'.indd')),false);
        // Templates open as untitled documents; reading page and layer counts still verifies native content.
        audit.native_reopen={pages:reopened.pages.length,layers:reopened.layers.length,items:reopened.allPageItems.length};
        reopened.close(SaveOptions.NO);
        write('audit.json',serialize(audit));
        write('COMPLETE.txt','Native InDesign generation and reopen passed. PDF/JPEG still require visual review.\n');
    } catch(e) {
        write('ERROR.txt',String(e)+'\nline='+e.line+'\n');
        if(doc){try{doc.close(SaveOptions.NO);}catch(ignore){}}
        throw e;
    } finally {
        try{app.pdfPlacePreferences.properties={pageNumber:oldPdfPage,pdfCrop:oldPdfCrop,transparentBackground:oldPdfBg};}catch(ignore){}
        try{app.jpegExportPreferences.properties=oldJpeg;}catch(ignore){}
        try{app.pdfExportPreferences.properties=oldPdfExport;}catch(ignore){}
        app.scriptPreferences.measurementUnit=oldUnit;
        app.scriptPreferences.userInteractionLevel=oldUI;
    }
})();
