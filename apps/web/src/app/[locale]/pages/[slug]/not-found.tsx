"use client";
import {useParams} from "next/navigation";
import {cmsMessages} from "../../../../lib/cms-messages";
export default function Missing(){const {locale}=useParams();const t=cmsMessages[locale==="ta"?"ta":"en"];return <main id="main"><h1>{t.unavailable}</h1><a href={`/${locale}/pages`}>{t.back}</a></main>;}
