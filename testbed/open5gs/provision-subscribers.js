// Provision testbed subscribers into the Open5GS subscriber DB (idempotent).
// K/OPc are the Open5GS sample test credentials; MSISDNs match the demo intents.
// Each UE gets a static IPv4 so the platform can resolve MSISDN -> UE IP for QoS requests.
db = db.getSiblingDB("open5gs");

const SUBSCRIBERS = [
  { imsi: "999700000000001", msisdn: "905321234567", ipv4: "10.45.0.10" },
  { imsi: "999700000000002", msisdn: "12025550180", ipv4: "10.45.0.11" },
  { imsi: "999700000000003", msisdn: "905551112233", ipv4: "10.45.0.12" },
];

const ambr = { downlink: { value: 1, unit: 3 }, uplink: { value: 1, unit: 3 } };

// PCC rules the PCF may install when an AF (via NEF) requests QoS for a media
// component: 5QI 1 = conversational voice (AUDIO), 5QI 2 = conversational video (VIDEO).
// Bit rates are upper bounds (unit 2 = Mbps); the AF's marBwUl/Dl applies within them.
const pccRule = (index) => ({
  qos: {
    index: index,
    arp: { priority_level: 2, pre_emption_capability: 2, pre_emption_vulnerability: 2 },
    mbr: { downlink: { value: 20, unit: 2 }, uplink: { value: 20, unit: 2 } },
    gbr: { downlink: { value: 20, unit: 2 }, uplink: { value: 20, unit: 2 } },
  },
  flow: [],
});

for (const s of SUBSCRIBERS) {
  db.subscribers.updateOne(
    { imsi: s.imsi },
    {
      $set: {
        imsi: s.imsi,
        msisdn: [s.msisdn],
        imeisv: [],
        mme_host: [],
        mme_realm: [],
        purge_flag: [],
        security: {
          k: "465B5CE8B199B49FAA5F0A2EE238A6BC",
          opc: "E8ED289DEBA952E4283B54E88E6183CA",
          op: null,
          amf: "8000",
          sqn: NumberLong("97"),
        },
        ambr: ambr,
        slice: [
          {
            sst: 1,
            default_indicator: true,
            session: [
              {
                name: "internet",
                type: 3,
                qos: {
                  index: 9,
                  arp: { priority_level: 8, pre_emption_capability: 1, pre_emption_vulnerability: 1 },
                },
                ambr: ambr,
                ue: { ipv4: s.ipv4 },
                pcc_rule: [pccRule(1), pccRule(2)],
              },
            ],
          },
        ],
        access_restriction_data: 32,
        subscriber_status: 0,
        operator_determined_barring: 0,
        network_access_mode: 0,
        subscribed_rau_tau_timer: 12,
        schema_version: 1,
        __v: 0,
      },
    },
    { upsert: true }
  );
  print(`provisioned imsi-${s.imsi} msisdn +${s.msisdn} ue ${s.ipv4}`);
}
