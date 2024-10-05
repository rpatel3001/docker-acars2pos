console.log("running");

import * as declib from '@airframes/acars-decoder';
import * as net from 'net';
import * as ndjson from 'ndjson';
import DatabaseConstructor, {Database, Statement} from 'better-sqlite3';

interface SBS {
    msg_type: string,
    msg_subtype: string,
    session_id: string,
    aircraft_id: string,
    icao: string,
    flight_id: string,
    send_time: string,
    log_time: string,
    callsign: string,
    altitude: string,
    ground_speed: string,
    ground_track: string,
    latitude: string,
    longitude: string,
    vertical_rate: string,
    squawk: string,
    alert: string,
    emergency: string,
    spi: string,
    on_ground: string,
}

function newSBS(): SBS {
    return {
        msg_type: "MSG",
        msg_subtype: "3",
        session_id: "1",
        aircraft_id: "1",
        icao: "",
        flight_id: "1",
        send_time: "",
        log_time: "",
        callsign: "",
        altitude: "",
        ground_speed: "",
        ground_track: "",
        latitude: "",
        longitude: "",
        vertical_rate: "",
        squawk: "",
        alert: "",
        emergency: "0",
        spi: "",
        on_ground: "",
    }
}

const icaodb: Database = new DatabaseConstructor('/opt/basestation/BaseStation.sqb');
const geticao: Statement = icaodb.prepare("SELECT ModeS FROM Aircraft WHERE Registration == ?");

function reg2icao(reg: string): string {
    reg = reg.replace(/[^a-zA-Z0-9-]/g,"");
    let res: any = geticao.get(reg);
    if (res && "ModeS" in res) {
        return res.ModeS;
    }
    return "";
}

function genSBS(sbs: SBS): string {
    return Object.values(sbs).join(",") + "\r\n";
//    return "MSG,3,1,1," + {sbs["icao"].upper()} + ",1," + {sbs_timestamp} + "," + {sbs_timestamp} + "," + {sbs_callsign} + "," + {sbs["alt"]} + ",,," + {latstr},{lonstr},,{squawk},,0,,'
}

const emptySBS: SBS = newSBS();

let dec: declib.MessageDecoder = new declib.MessageDecoder();

const acarssock: net.Socket = net.connect(Number(process.env.ACARSPORT), process.env.ACARSHOST);
acarssock.setEncoding('utf8');
acarssock.pipe(ndjson.parse()).on('data', parsea);

const vdlm2sock: net.Socket = net.connect(Number(process.env.VDLM2PORT), process.env.VDLM2HOST);
vdlm2sock.setEncoding('utf8');
vdlm2sock.pipe(ndjson.parse()).on('data', parsev);

const hfdlsock: net.Socket = net.connect(Number(process.env.HFDLPORT), process.env.HFDLHOST);
hfdlsock.setEncoding('utf8');
hfdlsock.pipe(ndjson.parse()).on('data', parseh);

const sbssock: net.Socket = net.connect(Number(process.env.SBSPORT), process.env.SBSHOST);
sbssock.setEncoding('utf8');

function parsea(msg: any): void {
    console.log("acars");
    const out: SBS = newSBS();
    out.squawk = "1000";
    if ("tail" in msg) {
        out.icao = reg2icao(msg.tail);
    }
    const res = parse(msg, out);
}

function parsev(msg: any): void {
    console.log("vdlm2");
    const out: SBS = newSBS();
    out.squawk = "2000";

    if ("vdl2" in msg) {
        msg = msg.vdl2;
    }
    if ("avlc" in msg) {
        msg = msg.avlc;
    }

    out.icao = msg.src.addr;

    if ("xid" in msg && "vdl_params" in msg.xid) {
        for (const p of msg.xid.vdl_params) {
            if (p.name === "ac_location") {
                console.log("xid");
                out.squawk = (parseInt(out.squawk, 10) + 1).toString();
                out.altitude = p.value.alt;
                out.latitude = p.value.loc.lat;
                out.longitude = p.value.loc.lon;
            }
        }
    }

    if ("acars" in msg) {
        msg = msg.acars;
    }
    if ("msg_text" in msg) {
        msg.text = msg.msg_text;
        delete msg.msg_text;
    }

    if ("reg" in msg) {
        out.icao = reg2icao(msg.reg);
    }

    const res = parse(msg, out);
}

function parseh(msg: any): void {
    console.log("hfdl");
    const out: SBS = newSBS();
    out.squawk = "3000";

    if ("hfdl" in msg) {
        msg = msg.hfdl;
    }
    if ("lpdu" in msg) {
        msg = msg.lpdu;
    }
    if ("hfnpdu" in msg) {
        msg = msg.hfnpdu;
    }

    if ("flight_id" in msg) {
        out.callsign = msg.flight_id;
    }

    if ("pos" in msg) {
        console.log("hfnpdu");
        out.squawk = (parseInt(out.squawk, 10) + 1).toString();
        out.latitude = msg.pos.lat;
        out.longitude = msg.pos.lon;
    }

    if ("acars" in msg) {
        msg = msg.acars;
    }
    if ("msg_text" in msg) {
        msg.text = msg.msg_text;
        delete msg.msg_text;
    }

    if ("reg" in msg) {
        out.icao = reg2icao(msg.reg);
    }

    const res = parse(msg, out);
}

function parse(msg: any, out: SBS): void {
//    if (!("text" in msg) || !msg.text) {
//        //console.log(msg);
//        return;
//    }

    let decmsg: any;
    try {
        decmsg = dec.decode(msg);
    } catch(e: any) {
        console.log(e);
        return;
    }

    if ("flight" in msg) {
        out.callsign = msg.flight;
    }

    const dts = new Date().toISOString().replaceAll("-", "/").replace("T", ",").replace("Z", "");
    out.send_time = dts;
    out.log_time = dts;

    if (decmsg.decoded) {
        out.squawk = (parseInt(out.squawk, 10) + 9).toString();
        console.log(decmsg.raw);

        if ("position" in decmsg.raw) {
            out.latitude = decmsg.raw.position.latitude;
            out.longitude = decmsg.raw.position.longitude;
        }
        if ("altitude" in decmsg.raw) {
            out.altitude = decmsg.raw.altitude;
        }
        if ("groundspeed" in decmsg.raw) {
            out.ground_speed = decmsg.raw.groundspeed;
        }
    }

    if (out.icao) {
//        console.log(out);
        console.log(genSBS(out));
        sbssock.write(genSBS(out));
    }

    console.log("");
}
