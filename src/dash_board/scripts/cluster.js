var supervisor = null

function drop_handler(ev) {
    ev.preventDefault();
    var files = ev.dataTransfer.files;
    var file = files[0];
    if(file) {
        var reader = new FileReader();
        reader.onload = function(e2) {
            document.getElementById("config").innerHTML = set_config(e2.target.result);
        };
        reader.readAsText(file);
    }
}
function dragover_handler(ev) {
  console.log("dragOver");
  ev.preventDefault();
}
function dragend_handler(ev) {
  console.log("dragEnd");
  var dt = ev.dataTransfer;
  if (dt.items) {
    var i = 0;
    for(i = 0; i < dt.items.length; i+=1) {
      dt.items.remove(i);
    }
  }
}

function set_config(file_content) {
    var json_string = JSON.parse(file_content);
    supervisor = load_supervisor(json_string);
    
    console.log(supervisor);
    var msg = supervisor.to_html();
    return msg;
}

class Unit {
    constructor(name, ip) {
        this.name = name;
        this.ip = ip;
    }
    
    to_html() {
        var n = "\t<div class=\"Header\" id=\"name\">" + this.name + "</div>\n";
        var i = "\t<div class=\"BoxContent\"><div id=\"ip\">" + this.ip + "</div>\n";
        var infos = n + "<div class=\"UnitInfos\">\n" + i + "</div>\n";
        return infos;
    }
}
class Job {
    constructor(name, port, jobname, debuglevel, jobdata = null, outputmethod = null, output = null) {
        this.name = name;
        this.port = port;
        this.jobname = jobname;
        this.debuglevel = debuglevel;
        this.jobdata = jobdata;
        this.outpoutmethod = outputmethod;
        this.output = output;
    }
    
    to_html() {
        var infos = "\t<div class=\"UnitJob\">\n";
        var n = "\t<div class=\"Header\" id=\"name\">" + this.name + "</div>\n";
        
        var s = "<div class=\"JobInfos\"><div class=\"BoxContent\">";
        var jn = "\t<div id=\"jobname\">" + this.jobname + "</div>\n";
        var p = "\t<div id=\"port\">" + this.port + "</div>\n";
        var dl = "\t<div id=\"debuglevel\">" + this.debuglevel + "</div>\n";
        infos += n + s + jn + p + dl;
        
        if(this.jobdata) {
            var jd = "\t<div id=\"jobdata\">" + this.jobdata + "</div>\n";
            infos += jd;
        }
        if(this.outpoutmethod) {
            var om = "\t<div id=\"outputmethod\">" + this.outpoutmethod + "</div>\n";
            infos += om;
        }
        
        infos += "</div>";
        
        if(this.output) {
            var o = "\t<div id=\"output\">" + this.output + "</div>\n";
            infos += o;
        }
        
        infos += "</div></div>\n";
        return infos;
    }
}
class Supervisor {
    constructor(port) {
        this.port = port;
        this.units = [];
        this.workers = {};
    }
    
    add_unit(unit, workers) {
        if(!(unit.name in this.units)) {
            this.units.push(unit);
            for(var worker in workers) {
                var json_worker = workers[worker];
                if(unit.name in this.workers)
                    this.workers[unit.name].push(json_worker);
                else
                    this.workers[unit.name] = [json_worker];
            }
        }
    }
    
    add_worker_to_unit(worker, unit) {
        if(unit in this.units) {
            if(!(worker in this.workers[unit.name]))
                this.workers[unit.name].push(worker);
        }
    }
    
    to_html() {
        var html_units = "\t<div class=\"Cluster\">\n\t<div class=\"Header\">Cluster</div>\n<div class=\"ClusterInfos\">\n<div class=\"BoxContent\">\n";
        html_units += "\t<div id=\"port\">" + this.port + "</div>\n</div>\n";
        var i = 0;
        for(i = 0; i < this.units.length; i+=1) {
            html_units += "\t<div class=\"Unit\">\n";
            
            var unit = this.units[i];
            html_units += unit.to_html(); 
            
            var jobs = this.workers[unit.name];
            var html_jobs = "";
            var j = 0;
            for(j = 0; j < jobs.length; j+=1) {
                var job = jobs[j];
                html_jobs += job.to_html();
            }
            
            html_units += "\t<div class=\"UnitJobs\">" + html_jobs + "</div>\n";
            html_units += "</div>\n</div>\n";
        }
        html_units += "</div></div>\n";
        return html_units;
    }
}

function load_supervisor(json_string) {
	var supervisor = new Supervisor(json_string["supervisorport"]);

	var units = [];
    var json_units = json_string["units"]
	for(var unit in json_units) {
        var json_unit = json_units[unit];
        var u = new Unit(json_unit["name"], json_unit["address"]);
		units.push(u);
    }

	var workers = {};
	var workers_data = json_string["workers"];
	for(var unit in units) {
        var json_unit = units[unit];
		var all_infos = workers_data[json_unit.name];
		for(var infos in all_infos) {
            var json_infos = all_infos[infos];
			var workername = json_infos["workername"];
			var port = json_infos["port"];
			var jobname = json_infos["jobname"];
			var debuglevel = json_infos["debuglevel"];
			var jobdata = null;
            if("jobdata" in json_infos)
                jobdata = json_infos["jobdata"];
			var outputmethod = null;
            if("outputmethod" in json_infos)
                outputmethod = json_infos["outputmethod"];
			var output = null;
            if("output" in json_infos)
                output = json_infos["output"];
			var job = new Job(workername, port, jobname, debuglevel, jobdata, outputmethod, output);
			if(json_unit.name in workers) {
				workers[json_unit.name].push(job);
            }
			else {
				workers[json_unit.name] = [job];
            }
        }
    }

	for(var unit in units) {
        var json_unit = units[unit];
        var unit_name = json_unit.name;
		supervisor.add_unit(json_unit, workers[unit_name]);
    }
    
	return supervisor;
}